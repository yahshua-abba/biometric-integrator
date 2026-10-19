"""
End-to-end scenarios for getting a punch from the device into Payroll.

Every test runs the real Database, PullService, PushService and SyncScheduler
against a fake ZKTeco device and a fake YAHSHUA Payroll server, so the whole
path (pull -> local queue -> upload -> Payroll answer -> local state) is covered.

Run with:
    cd backend && python -m pytest tests/test_sync_scenarios.py -v
"""

import threading
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import requests
from urllib3.exceptions import MaxRetryError, NewConnectionError

from database import Database
from services import pull_service as pull_module
from services.pull_service import PullService
from services.push_service import PushService
from services.scheduler import SyncScheduler, CLEANUP_DAYS


TODAY = datetime.now().replace(microsecond=0)


# ---------------------------------------------------------------------------
# Fake ZKTeco device
# ---------------------------------------------------------------------------

def punch(user_id, when, kind=0):
    return SimpleNamespace(user_id=user_id, timestamp=when, punch=kind)


class FakeDevice:
    def __init__(self, logs=(), users=(), fail_connect=False):
        self.logs = list(logs)
        self.users = list(users)
        self.fail_connect = fail_connect

    # ZK(...).connect() returns the connection object; reuse self for both.
    def connect(self):
        if self.fail_connect:
            raise Exception('Device unreachable')
        return self

    def get_attendance(self):
        return list(self.logs)

    def get_users(self):
        ids = {str(u) for u in self.users} | {str(l.user_id) for l in self.logs}
        return [SimpleNamespace(user_id=u, name=f'Employee {u}') for u in sorted(ids)]

    def disconnect(self):
        pass


@pytest.fixture
def devices(monkeypatch):
    """Map device IP -> FakeDevice; PullService's ZK(...) resolves through it."""
    by_ip = {}
    monkeypatch.setattr(pull_module, 'ZK', lambda ip, **kw: by_ip[ip])
    return by_ip


# ---------------------------------------------------------------------------
# Fake YAHSHUA Payroll
# ---------------------------------------------------------------------------

def response(status, body, raw=None):
    resp = MagicMock(status_code=status)
    if raw is not None:
        resp.json.side_effect = ValueError('not JSON')
        resp.text = raw
    else:
        resp.json.return_value = body
        resp.text = str(body)
    return resp


def no_internet():
    reason = NewConnectionError(None, 'Failed to establish a new connection')
    return requests.exceptions.ConnectionError(MaxRetryError(None, '/api', reason=reason))


class FakePayroll:
    """Behaves like YAHSHUA's /sync-time-in-out/ endpoint.

    employees: Biometrics IDs that exist in Payroll.
    shared_ids: Biometrics IDs set on two employees (Payroll crashes on these).
    outage: None, or one of 'no_internet', 'timeout', 'expired', 'html_502', 'garbage'
            applied to every push request.
    """

    def __init__(self, employees=(), shared_ids=()):
        self.employees = {str(e) for e in employees}
        self.shared_ids = {str(e) for e in shared_ids}
        self.stored = {}          # sync_id -> number of times stored
        self.requests = []        # list of request sizes
        self.outage = None
        self.logins = 0
        self.lock = threading.Lock()

    def post(self, url, json=None, **kwargs):
        if url.endswith('/api-auth/'):
            if self.outage == 'no_internet':
                raise no_internet()
            self.logins += 1
            return response(200, {'token': f'token-{self.logins}', 'user_logged': 'HR', 'company_name': 'LCG'})
        with self.lock:
            return self._sync(json['log_list'])

    def _sync(self, log_list):
        self.requests.append(len(log_list))
        if self.outage == 'no_internet':
            raise no_internet()
        if self.outage == 'expired':
            return response(401, {'detail': 'Invalid token.'})
        if self.outage == 'html_502':
            return response(502, None, raw='<html>Bad Gateway</html>')
        if self.outage == 'garbage':
            return response(200, 'OK')
        if self.outage == 'timeout':
            # Payroll stored the logs but the answer never arrived.
            for log in log_list:
                self.stored[log['sync_id']] = self.stored.get(log['sync_id'], 0) + 1
            raise requests.exceptions.ReadTimeout()
        if any(str(log['employee']) in self.shared_ids for log in log_list):
            return response(400, "get() returned more than one Employee -- it returned 2!")
        synced, failed = [], []
        for log in log_list:
            if str(log['employee']) not in self.employees:
                failed.append({'id': log['id'], 'reason': 'No Employee', 'error_code': 2})
            elif log['sync_id'] in self.stored:
                failed.append({'id': log['id'], 'reason': 'Sync ID already exists.', 'error_code': 1})
            else:
                self.stored[log['sync_id']] = 1
                synced.append(log['id'])
        return response(200, {'logs_successfully_sync': synced, 'logs_not_sync': failed,
                              'has_error': bool(failed)})


# ---------------------------------------------------------------------------
# App wiring
# ---------------------------------------------------------------------------

class App:
    def __init__(self, tmp_path, devices, payroll, payroll_2=None):
        self.db = Database(str(tmp_path / 'attendance.db'))
        self.db.update_api_config(push_username='hr', push_password='secret',
                                  push_url='https://payroll.test/api')
        self.devices = devices
        self.pull = PullService(self.db)
        self.push = PushService(self.db, 1)
        self.push.session.post = payroll.post
        self.push_2 = PushService(self.db, 2)
        if payroll_2:
            self.push_2.session.post = payroll_2.post
        self.scheduler = SyncScheduler(self.pull, self.push, self.db, self.push_2)

    def add_device(self, name, ip, device, branch_id=None):
        self.devices[ip] = device
        return self.db.add_device(name, ip, branch_id=branch_id)

    def rows(self):
        return {r['sync_id']: r for r in self.db.get_all_timesheets()}

    def row(self, sync_id):
        return self.rows()[sync_id]

    def attempt(self, sync_id, slot=1):
        conn = self.db.get_connection()
        try:
            row = conn.execute('SELECT * FROM delivery_attempt WHERE sync_id=? AND slot=?',
                               (sync_id, slot)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def pending(self, slot=1):
        return [r['sync_id'] for r in self.db.get_unsynced_timesheets(limit=100000, slot=slot)]


def sid(device_id, user_id, when):
    return f"ZK_{device_id}_{user_id}_{when.strftime('%Y%m%d%H%M%S')}"


@pytest.fixture
def payroll():
    return FakePayroll(employees=['101', '102', '103', 'A-7'])


@pytest.fixture
def app(tmp_path, devices, payroll):
    return App(tmp_path, devices, payroll)


# ===========================================================================
# 1. Pulling from devices
# ===========================================================================

class TestPull:
    @pytest.mark.parametrize('kind,expected', [(0, 'in'), (1, 'out'), (2, 'out'), (3, 'in'),
                                               (4, 'in'), (5, 'out'), (None, 'in')])
    def test_punch_types_map_to_in_or_out(self, app, kind, expected):
        when = TODAY.replace(hour=8, minute=0, second=0)
        dev = app.add_device('Lobby', '10.0.0.1', FakeDevice([punch('101', when, kind)]))
        app.pull.pull_data()
        assert app.row(sid(dev, '101', when))['log_type'] == expected

    def test_pulling_the_same_logs_again_adds_nothing(self, app):
        when = TODAY.replace(hour=8, minute=0, second=0)
        app.add_device('Lobby', '10.0.0.1', FakeDevice([punch('101', when)]))
        _, _, first = app.pull.pull_data()
        _, _, second = app.pull.pull_data()
        assert first['new_records'] == 1
        assert second['new_records'] == 0 and second['duplicates'] == 1
        assert len(app.rows()) == 1

    def test_same_person_same_second_on_two_devices_is_two_records(self, app):
        when = TODAY.replace(hour=8, minute=0, second=0)
        a = app.add_device('Basement', '10.0.0.1', FakeDevice([punch('101', when)]))
        b = app.add_device('Ground', '10.0.0.2', FakeDevice([punch('101', when)]))
        app.pull.pull_data()
        assert {sid(a, '101', when), sid(b, '101', when)} == set(app.rows())

    def test_one_unreachable_device_does_not_block_the_others(self, app):
        when = TODAY.replace(hour=8, minute=0, second=0)
        app.add_device('Broken', '10.0.0.1', FakeDevice(fail_connect=True))
        ok = app.add_device('Ground', '10.0.0.2', FakeDevice([punch('101', when)]))
        success, message, stats = app.pull.pull_data()
        assert success and stats['devices_failed'] == 1 and stats['devices_synced'] == 1
        assert sid(ok, '101', when) in app.rows()

    def test_one_bad_log_does_not_stop_the_rest(self, app):
        when = TODAY.replace(hour=8, minute=0, second=0)
        bad = SimpleNamespace(user_id='101', timestamp=None, punch=0)  # corrupt clock entry
        dev = app.add_device('Lobby', '10.0.0.1', FakeDevice([bad, punch('102', when)]))
        _, _, stats = app.pull.pull_data()
        assert stats['errors'] == 1
        assert sid(dev, '102', when) in app.rows()

    def test_explicit_date_range_skips_logs_outside_it(self, app):
        old = TODAY - timedelta(days=10)
        dev = app.add_device('Lobby', '10.0.0.1', FakeDevice([punch('101', old), punch('102', TODAY)]))
        app.pull.pull_data(date_from=TODAY.strftime('%Y-%m-%d'), date_to=TODAY.strftime('%Y-%m-%d'))
        assert set(app.rows()) == {sid(dev, '102', TODAY)}

    def test_scheduled_pull_catches_up_after_the_pc_was_off_for_days(self, app):
        """PC off Friday night to Monday: weekend punches must still reach Payroll."""
        saturday = TODAY - timedelta(days=2)
        dev = app.add_device('Lobby', '10.0.0.1', FakeDevice([punch('101', saturday)]))
        conn = app.db.get_connection()
        conn.execute('UPDATE device SET last_pull_at=? WHERE id=?', (TODAY - timedelta(days=3), dev))
        conn.commit()
        conn.close()
        app.scheduler.run_pull_sync()
        assert sid(dev, '101', saturday) in app.rows()

    def test_scheduled_catch_up_is_capped(self, app):
        """A device last seen a year ago must not flood Payroll with a year of history."""
        ancient = TODAY - timedelta(days=200)
        dev = app.add_device('Lobby', '10.0.0.1', FakeDevice([punch('101', ancient), punch('102', TODAY)]))
        conn = app.db.get_connection()
        conn.execute('UPDATE device SET last_pull_at=? WHERE id=?', (TODAY - timedelta(days=365), dev))
        conn.commit()
        conn.close()
        app.scheduler.run_pull_sync()
        assert set(app.rows()) == {sid(dev, '102', TODAY)}

    def test_new_device_only_pulls_recent_logs(self, app):
        dev = app.add_device('Lobby', '10.0.0.1', FakeDevice([punch('101', TODAY - timedelta(days=5)),
                                                              punch('102', TODAY)]))
        app.scheduler.run_pull_sync()
        assert set(app.rows()) == {sid(dev, '102', TODAY)}

    def test_deleted_log_is_not_re_added_or_uploaded_when_device_resends_it(self, app, payroll):
        dev = app.add_device('Lobby', '10.0.0.1', FakeDevice([punch('101', TODAY)]))
        app.pull.pull_data()
        row = app.row(sid(dev, '101', TODAY))
        app.db.soft_delete_timesheets_by_ids([row['id']])
        app.pull.pull_data()
        app.push.push_data()
        assert payroll.stored == {}


# ===========================================================================
# 2. Normal uploads
# ===========================================================================

class TestUpload:
    def test_successful_upload_is_never_sent_again(self, app, payroll):
        dev = app.add_device('Lobby', '10.0.0.1', FakeDevice([punch('101', TODAY)]))
        app.pull.pull_data()
        ok, _, stats = app.push.push_data()
        assert ok and stats['success'] == 1
        assert app.row(sid(dev, '101', TODAY))['backend_timesheet_id'] is not None
        app.pull.pull_data()
        app.push.push_data()
        assert payroll.stored == {sid(dev, '101', TODAY): 1}
        assert payroll.requests == [1]

    def test_branch_and_alphanumeric_ids_are_sent_as_is(self, app, payroll):
        sent = []
        original = payroll._sync
        payroll._sync = lambda logs: (sent.extend(logs), original(logs))[1]
        app.add_device('Lobby', '10.0.0.1', FakeDevice([punch('A-7', TODAY)]), branch_id='MAIN')
        app.pull.pull_data()
        app.push.push_data()
        assert sent[0]['employee'] == 'A-7' and sent[0]['branch_id'] == 'MAIN'
        assert sent[0]['log_type'] == 'IN' and sent[0]['date'] == TODAY.strftime('%Y-%m-%d')

    def test_mixed_answers_land_in_the_right_place(self, app, payroll):
        payroll.stored['ZK_already_there'] = 1
        dev = app.add_device('Lobby', '10.0.0.1', FakeDevice([
            punch('101', TODAY.replace(hour=8)),   # good
            punch('999', TODAY.replace(hour=8)),   # not in Payroll
        ]))
        app.pull.pull_data()
        _, _, stats = app.push.push_data()
        assert stats['success'] == 1 and stats['failed'] == 1
        unknown = app.row(sid(dev, '999', TODAY.replace(hour=8)))
        assert unknown['sync_error_message'] == 'No Employee'
        assert app.attempt(unknown['sync_id'])['outcome'] == 'failed'
        # Failed logs wait for HR in the Retry Queue; the scheduler never resends them.
        payroll.requests.clear()
        app.push.push_data()
        assert payroll.requests == []

    def test_payroll_already_has_this_sync_id_counts_as_delivered(self, app, payroll):
        """Payroll stored it earlier but the answer was lost; it must not sit in the Retry Queue forever."""
        dev = app.add_device('Lobby', '10.0.0.1', FakeDevice([punch('101', TODAY)]))
        app.pull.pull_data()
        key = sid(dev, '101', TODAY)
        payroll.stored[key] = 1
        _, _, stats = app.push.push_data()
        assert stats['failed'] == 0 and stats['duplicates'] == 1
        assert app.row(key)['sync_error_message'] is None
        assert app.attempt(key)['outcome'] == 'resolved'

    def test_record_payroll_does_not_mention_is_unconfirmed(self, app, payroll):
        dev = app.add_device('Lobby', '10.0.0.1', FakeDevice([punch('101', TODAY)]))
        app.pull.pull_data()
        payroll._sync = lambda logs: response(200, {'logs_successfully_sync': [], 'logs_not_sync': []})
        app.push.push_data()
        assert app.attempt(sid(dev, '101', TODAY))['outcome'] == 'unconfirmed'

    def test_many_logs_go_in_batches_of_50_each_sent_once(self, app, payroll):
        logs = [punch('101', TODAY.replace(hour=0, minute=0, second=0) + timedelta(seconds=i)) for i in range(120)]
        app.add_device('Lobby', '10.0.0.1', FakeDevice(logs))
        app.pull.pull_data(date_from=TODAY.strftime('%Y-%m-%d'))
        _, _, stats = app.push.push_data()
        assert payroll.requests == [50, 50, 20]
        assert stats['success'] == 120 and set(payroll.stored.values()) == {1}

    def test_backlog_bigger_than_one_run_drains_over_runs(self, app, payroll, monkeypatch):
        logs = [punch('101', TODAY.replace(hour=0, minute=0, second=0) + timedelta(seconds=i)) for i in range(30)]
        app.add_device('Lobby', '10.0.0.1', FakeDevice(logs))
        app.pull.pull_data(date_from=TODAY.strftime('%Y-%m-%d'))
        real = app.db.get_unsynced_timesheets
        monkeypatch.setattr(app.db, 'get_unsynced_timesheets', lambda limit=100, slot=1: real(limit=12, slot=slot))
        for _ in range(3):
            app.push.push_data()
        assert len(payroll.stored) == 30 and app.pending() == []


# ===========================================================================
# 3. The LCG case: old failures and one broken employee must not hide new punches
# ===========================================================================

class TestStuckQueue:
    def test_todays_punch_reaches_payroll_despite_old_failures_and_a_shared_id(self, tmp_path, devices):
        payroll = FakePayroll(employees=['101', '555'], shared_ids=['555'])
        app = App(tmp_path, devices, payroll)
        yesterday = TODAY - timedelta(hours=20)
        old = [punch(str(900 + i % 40), yesterday + timedelta(seconds=i)) for i in range(260)]
        shared = [punch('555', yesterday + timedelta(seconds=300))]
        fresh = [punch('101', TODAY)]
        dev = app.add_device('Basement', '10.0.0.1', FakeDevice(old + shared + fresh))
        app.scheduler.run_pull_sync()
        app.scheduler.run_push_sync()
        assert payroll.stored == {sid(dev, '101', TODAY): 1}
        shared_row = app.row(sid(dev, '555', yesterday + timedelta(seconds=300)))
        assert 'More than one employee' in shared_row['sync_error_message']
        # Next run sends nothing old again; only new punches.
        payroll.requests.clear()
        app.scheduler.run_push_sync()
        assert payroll.requests == []

    def test_fixing_the_employee_then_retrying_from_the_queue_syncs(self, app, payroll):
        dev = app.add_device('Lobby', '10.0.0.1', FakeDevice([punch('777', TODAY)]))
        app.pull.pull_data()
        app.push.push_data()
        row = app.row(sid(dev, '777', TODAY))
        assert row['sync_error_message'] == 'No Employee'
        payroll.employees.add('777')
        ok, _, stats = app.push.push_data(timesheet_ids=[row['id']], manual_retry=True)
        assert ok and stats['success'] == 1
        assert app.attempt(row['sync_id'])['outcome'] == 'resolved'

    def test_manual_retry_of_a_log_payroll_already_has_clears_it(self, app, payroll):
        dev = app.add_device('Lobby', '10.0.0.1', FakeDevice([punch('101', TODAY)]))
        app.pull.pull_data()
        payroll.outage = 'timeout'
        app.push.push_data()
        key = sid(dev, '101', TODAY)
        assert app.attempt(key)['outcome'] == 'unconfirmed'
        payroll.outage = None
        app.push.push_data(timesheet_ids=[app.row(key)['id']], manual_retry=True)
        assert app.attempt(key)['outcome'] == 'resolved'
        assert payroll.stored[key] == 1


# ===========================================================================
# 4. Internet and Payroll outages
# ===========================================================================

class TestOutages:
    def _one_punch(self, app):
        dev = app.add_device('Lobby', '10.0.0.1', FakeDevice([punch('101', TODAY)]))
        app.pull.pull_data()
        return sid(dev, '101', TODAY)

    def test_no_internet_keeps_logs_in_the_automatic_queue(self, app, payroll):
        key = self._one_punch(app)
        app.db.update_push_token('token-0')
        payroll.outage = 'no_internet'
        ok, message, _ = app.push.push_data()
        assert not ok and 'connect' in message.lower()
        assert app.attempt(key) is None and app.row(key)['sync_error_message'] is None
        payroll.outage = None
        app.push.push_data()
        assert payroll.stored == {key: 1}

    def test_no_internet_during_login_touches_nothing(self, app, payroll):
        key = self._one_punch(app)
        payroll.outage = 'no_internet'
        ok, _, _ = app.push.push_data()
        assert not ok and app.attempt(key) is None
        payroll.outage = None
        app.push.push_data()
        assert payroll.stored == {key: 1}

    def test_expired_login_logs_in_again_and_sends_in_the_same_run(self, app, payroll):
        key = self._one_punch(app)
        app.db.update_push_token('stale-token')
        original = payroll._sync

        def expired_once(log_list):
            payroll._sync = original
            return response(401, {'detail': 'Invalid token.'})
        payroll._sync = expired_once
        ok, _, stats = app.push.push_data()
        assert ok and stats['success'] == 1
        assert payroll.stored == {key: 1} and payroll.logins == 1
        assert app.attempt(key)['outcome'] == 'resolved'

    def test_login_refused_even_after_logging_in_again_keeps_logs_automatic(self, app, payroll):
        key = self._one_punch(app)
        app.db.update_push_token('stale-token')
        payroll.outage = 'expired'
        ok, _, _ = app.push.push_data()
        assert not ok and app.attempt(key) is None
        assert app.db.get_push_token() is None
        payroll.outage = None
        app.push.push_data()
        assert payroll.stored == {key: 1} and payroll.logins == 2

    def test_timeout_after_sending_goes_to_review_not_resent_automatically(self, app, payroll):
        key = self._one_punch(app)
        payroll.outage = 'timeout'
        app.push.push_data()
        assert app.attempt(key)['outcome'] == 'unconfirmed'
        payroll.outage = None
        app.push.push_data()
        assert payroll.stored[key] == 1  # Payroll got it once; the app did not double it

    def test_gateway_error_page_gets_a_readable_message(self, app, payroll):
        key = self._one_punch(app)
        payroll.outage = 'html_502'
        ok, message, _ = app.push.push_data()
        assert not ok
        assert 'temporarily unavailable' in app.row(key)['sync_error_message']
        assert app.attempt(key)['outcome'] == 'unconfirmed'

    def test_unreadable_ok_answer_is_unconfirmed(self, app, payroll):
        key = self._one_punch(app)
        payroll.outage = 'garbage'
        app.push.push_data()
        assert app.attempt(key)['outcome'] == 'unconfirmed'

    def test_internet_drop_midway_keeps_earlier_batches_and_requeues_the_rest(self, app, payroll):
        logs = [punch('101', TODAY.replace(hour=0, minute=0, second=0) + timedelta(seconds=i)) for i in range(120)]
        app.add_device('Lobby', '10.0.0.1', FakeDevice(logs))
        app.pull.pull_data(date_from=TODAY.strftime('%Y-%m-%d'))
        original = payroll._sync
        calls = []

        def flaky(log_list):
            calls.append(1)
            if len(calls) == 2:
                raise no_internet()
            return original(log_list)
        payroll._sync = flaky
        app.push.push_data()
        assert len(payroll.stored) == 50 and len(app.pending()) == 70
        payroll._sync = original
        app.push.push_data()
        assert len(payroll.stored) == 120 and set(payroll.stored.values()) == {1}

    def test_wrong_password_leaves_logs_waiting(self, app, payroll):
        key = self._one_punch(app)
        payroll.post = None
        app.push.session.post = lambda url, **kw: response(401, {'message': 'Invalid credentials'})
        ok, message, _ = app.push.push_data()
        assert not ok and 'Login failed' in message
        assert app.attempt(key) is None


# ===========================================================================
# 5. Do Not Sync and deleted logs
# ===========================================================================

class TestExclusions:
    def test_do_not_sync_is_never_sent_until_unmarked(self, app, payroll):
        dev = app.add_device('Lobby', '10.0.0.1', FakeDevice([punch('101', TODAY)]))
        app.pull.pull_data()
        row = app.row(sid(dev, '101', TODAY))
        app.db.set_timesheets_excluded([row['id']], True)
        app.push.push_data()
        assert payroll.stored == {}
        app.db.set_timesheets_excluded([row['id']], False)
        app.push.push_data()
        assert payroll.stored == {row['sync_id']: 1}

    def test_deleted_is_never_sent(self, app, payroll):
        dev = app.add_device('Lobby', '10.0.0.1', FakeDevice([punch('101', TODAY)]))
        app.pull.pull_data()
        app.db.soft_delete_timesheets_by_ids([app.row(sid(dev, '101', TODAY))['id']])
        app.push.push_data()
        assert payroll.stored == {}

    def test_do_not_sync_leaves_logs_already_sent_alone(self, tmp_path, devices):
        p1, p2 = FakePayroll(employees=['101']), FakePayroll(employees=['101'])
        app = App(tmp_path, devices, p1, p2)
        sent, waiting = TODAY.replace(hour=7), TODAY.replace(hour=9)
        device = FakeDevice([punch('101', sent)])
        dev = app.add_device('Lobby', '10.0.0.1', device)
        app.scheduler.run_pull_sync()
        app.scheduler.run_push_sync()
        device.logs.append(punch('101', waiting))
        app.scheduler.run_pull_sync()
        day = TODAY.strftime('%Y-%m-%d')
        assert app.db.set_timesheets_excluded([app.row(sid(dev, '101', sent))['id']], True) == 0
        assert app.db.set_timesheets_excluded_by_date_range(day, day, True) == 1
        assert not app.row(sid(dev, '101', sent))['excluded_from_sync']
        # Payroll 2 switched on later with all history still gets the log Payroll 1 has.
        app.db.update_api_config(push_enabled_2=1, push_username_2='hr2', push_password_2='x')
        app.scheduler.run_push_sync()
        assert set(p2.stored) == {sid(dev, '101', sent)}


# ===========================================================================
# 6. Two Payroll destinations
# ===========================================================================

class TestTwoDestinations:
    @pytest.fixture
    def dual(self, tmp_path, devices):
        p1, p2 = FakePayroll(employees=['101']), FakePayroll(employees=['101'])
        app = App(tmp_path, devices, p1, p2)
        app.db.update_api_config(push_enabled_2=1, push_username_2='hr2', push_password_2='secret2',
                                 push_url_2='https://payroll2.test/api')
        return app, p1, p2

    def test_each_destination_gets_each_log_once(self, dual):
        app, p1, p2 = dual
        dev = app.add_device('Lobby', '10.0.0.1', FakeDevice([punch('101', TODAY)]))
        app.scheduler.run_pull_sync()
        app.scheduler.run_push_sync()
        app.scheduler.run_push_sync()
        key = sid(dev, '101', TODAY)
        assert p1.stored == {key: 1} and p2.stored == {key: 1}

    def test_one_destination_down_does_not_hold_back_the_other(self, dual):
        app, p1, p2 = dual
        dev = app.add_device('Lobby', '10.0.0.1', FakeDevice([punch('101', TODAY)]))
        app.scheduler.run_pull_sync()
        p2.outage = 'no_internet'
        app.scheduler.run_push_sync()
        key = sid(dev, '101', TODAY)
        assert p1.stored == {key: 1} and p2.stored == {}
        p2.outage = None
        app.scheduler.run_push_sync()
        assert p1.stored == {key: 1} and p2.stored == {key: 1}

    def test_second_destination_added_later_gets_only_new_logs(self, tmp_path, devices):
        p1, p2 = FakePayroll(employees=['101']), FakePayroll(employees=['101'])
        app = App(tmp_path, devices, p1, p2)
        old_time, new_time = TODAY.replace(hour=7), TODAY.replace(hour=9)
        device = FakeDevice([punch('101', old_time)])
        dev = app.add_device('Lobby', '10.0.0.1', device)
        app.scheduler.run_pull_sync()
        app.scheduler.run_push_sync()
        app.db.update_api_config(push_enabled_2=1, push_username_2='hr2', push_password_2='x')
        app.db.baseline_slot_as_synced(2)
        device.logs.append(punch('101', new_time))
        app.scheduler.run_pull_sync()
        app.scheduler.run_push_sync()
        assert set(p2.stored) == {sid(dev, '101', new_time)}

    def test_turning_payroll_2_back_on_keeps_its_failed_logs_in_review(self, dual):
        app, p1, p2 = dual
        dev = app.add_device('Lobby', '10.0.0.1', FakeDevice([punch('101', TODAY)]))
        app.scheduler.run_pull_sync()
        p2.employees.clear()  # Payroll 2 answers "No Employee"
        app.scheduler.run_push_sync()
        key = sid(dev, '101', TODAY)
        assert app.attempt(key, 2)['outcome'] == 'failed'
        # Off, then on again without sending old history.
        app.db.update_api_config(push_enabled_2=0)
        app.db.baseline_slot_as_synced(2)
        app.db.update_api_config(push_enabled_2=1)
        assert app.row(key)['backend_timesheet_id_2'] is None
        assert [i['state'] for i in app.db.get_retry_queue({'slot': 2})] == ['failed']
        assert app.db.get_timesheet_stats()['synced'] == 0

    def test_clearing_synced_logs_keeps_ones_payroll_2_still_needs(self, dual):
        app, p1, p2 = dual
        dev = app.add_device('Lobby', '10.0.0.1', FakeDevice([punch('101', TODAY)]))
        app.scheduler.run_pull_sync()
        p2.outage = 'no_internet'
        app.scheduler.run_push_sync()
        day = TODAY.strftime('%Y-%m-%d')
        assert app.db.clear_timesheets(day, day, only_synced=True) == 0
        p2.outage = None
        app.scheduler.run_push_sync()
        assert p2.stored == {sid(dev, '101', TODAY): 1}
        assert app.db.clear_timesheets(day, day, only_synced=True) == 1


# ===========================================================================
# 7. Overlapping runs
# ===========================================================================

class TestConcurrency:
    def test_scheduled_and_manual_push_at_once_send_each_log_once(self, app, payroll):
        logs = [punch('101', TODAY.replace(hour=0, minute=0, second=0) + timedelta(seconds=i)) for i in range(150)]
        app.add_device('Lobby', '10.0.0.1', FakeDevice(logs))
        app.pull.pull_data(date_from=TODAY.strftime('%Y-%m-%d'))
        other = PushService(app.db, 1)  # e.g. the dashboard's own instance
        other.session.post = payroll.post
        threads = [threading.Thread(target=s.push_data) for s in (app.push, other, app.push, other)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(payroll.stored) == 150 and set(payroll.stored.values()) == {1}

    def test_pull_while_pushing_does_not_lose_or_double_logs(self, app, payroll):
        base = TODAY.replace(hour=0, minute=0, second=0)
        device = FakeDevice([punch('101', base + timedelta(seconds=i)) for i in range(60)])
        app.add_device('Lobby', '10.0.0.1', device)
        app.pull.pull_data(date_from=TODAY.strftime('%Y-%m-%d'))
        device.logs += [punch('102', base + timedelta(seconds=i)) for i in range(60)]
        t = threading.Thread(target=app.push.push_data)
        t.start()
        app.pull.pull_data(date_from=TODAY.strftime('%Y-%m-%d'))
        t.join()
        app.push.push_data()
        assert len(payroll.stored) == 120 and set(payroll.stored.values()) == {1}


# ===========================================================================
# 8. Nightly clean-up
# ===========================================================================

class TestCleanup:
    def _old_row(self, app, user='101'):
        when = TODAY - timedelta(days=CLEANUP_DAYS + 5)
        dev = app.add_device(f'Lobby {user}', f'10.0.1.{user[-1]}', FakeDevice([punch(user, when)]))
        day = when.strftime('%Y-%m-%d')
        app.pull.pull_data(date_from=day, date_to=day)
        return sid(dev, user, when), day

    def test_old_delivered_log_is_removed_and_never_resent_if_pulled_again(self, app, payroll):
        key, day = self._old_row(app)
        app.push.push_data()
        app.scheduler.run_cleanup()
        assert key not in app.rows()
        app.pull.pull_data(date_from=day, date_to=day)
        app.push.push_data()
        assert payroll.stored == {key: 1}

    def test_old_log_never_sent_is_kept_not_silently_deleted(self, app, payroll):
        key, _ = self._old_row(app)
        app.scheduler.run_cleanup()
        assert key in app.rows()

    def test_old_failed_log_stays_for_hr(self, app, payroll):
        key, _ = self._old_row(app, user='999')
        app.push.push_data()
        app.scheduler.run_cleanup()
        assert key in app.rows()

    def _fail_for_payroll_2(self, app, key):
        row_id = app.row(key)['id']
        app.db.claim_delivery([row_id], 2)
        app.db.mark_timesheet_sync_failed(row_id, 'No Employee', slot=2)

    def test_payroll_2_switched_on_without_a_login_does_not_stop_cleanup(self, app, payroll):
        key, _ = self._old_row(app)
        app.push.push_data()
        app.db.update_api_config(push_enabled_2=1)  # never logged in, so nothing is ever sent there
        app.scheduler.run_cleanup()
        assert key not in app.rows()

    def test_old_failure_for_a_switched_off_payroll_2_does_not_block_cleanup(self, app, payroll):
        key, _ = self._old_row(app)
        app.push.push_data()
        self._fail_for_payroll_2(app, key)  # while Payroll 2 was on
        app.scheduler.run_cleanup()
        assert key not in app.rows()

    def test_old_failure_for_payroll_2_stays_while_it_is_on(self, app, payroll):
        key, _ = self._old_row(app)
        app.push.push_data()
        app.db.update_api_config(push_enabled_2=1, push_username_2='hr2', push_password_2='x')
        self._fail_for_payroll_2(app, key)
        app.scheduler.run_cleanup()
        assert key in app.rows()

    def test_old_deleted_log_cleaned_up_then_pulled_again_is_not_sent(self, app, payroll):
        key, day = self._old_row(app)
        app.db.soft_delete_timesheets_by_ids([app.row(key)['id']])
        app.scheduler.run_cleanup()
        app.pull.pull_data(date_from=day, date_to=day)
        app.push.push_data()
        assert payroll.stored == {}

    def test_old_do_not_sync_log_cleaned_up_then_pulled_again_is_not_sent(self, app, payroll):
        key, day = self._old_row(app)
        app.db.set_timesheets_excluded([app.row(key)['id']], True)
        app.scheduler.run_cleanup()
        app.pull.pull_data(date_from=day, date_to=day)
        app.push.push_data()
        assert payroll.stored == {}
