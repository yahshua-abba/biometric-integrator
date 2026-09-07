"""Regression cases for deletion followed by a pending destination re-upload."""

import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import pytest

from database import Database
from services.push_service import PushService
from services.sync_errors import is_duplicate_error


@pytest.fixture
def seeded(tmp_path):
    db = Database(str(tmp_path / 'attendance.db'))
    db.add_or_update_employee('4472', 'Demo Employee', '4472')
    employee = db.get_employee_by_code('4472')['id']
    row = db.add_timesheet_entry('ZK_DEMO_4472_20260824185200', employee,
                                 'in', '2026-08-24', '18:52:00')
    db.update_api_config(push_enabled_2=1, push_username_2='demo')
    return db, row


def service(db, slot):
    svc = PushService(db, slot)
    svc.get_valid_token = lambda: 'test-token'
    svc.get_base_url = lambda: 'http://127.0.0.1:1/api'
    return svc


def reply(status, success=(), failed=()):
    resp = Mock(status_code=status)
    resp.json.return_value = {'logs_successfully_sync': list(success), 'logs_not_sync': list(failed)}
    return resp


@pytest.mark.parametrize('slot', [1, 2])
@pytest.mark.parametrize('status', [200, 400])
@pytest.mark.parametrize('code,reason', [(120, 'Duplicate record already exists'),
                                       ('120', 'Duplicate record already exists'),
                                       (1, 'Time in range (5mins)')])
def test_duplicate_cannot_return_after_payroll_deletion_or_app_restart(seeded, slot, status, code, reason):
    db, row = seeded
    svc = service(db, slot)
    svc.session.post = Mock(return_value=reply(status, failed=[{'id': row, 'error_code': code, 'reason': reason}]))
    success, message, stats = svc.push_data()
    assert success and stats['duplicates'] == 1 and stats['success'] == stats['failed'] == 0
    assert 'will not retry' in message
    suffix = '_2' if slot == 2 else ''
    saved = db.get_all_timesheets()[0]
    assert saved[f'backend_timesheet_id{suffix}'] is None  # never misrepresent an upload
    assert saved[f'sync_skipped_reason{suffix}'] == reason
    # HR deletes remotely; a restarted client must not even make an HTTP request.
    restarted = Database(str(db.db_path))
    svc = service(restarted, slot)
    svc.session.post = Mock(return_value=reply(200, [row]))
    svc.push_data(timesheet_ids=[row])
    svc.push_data()
    svc.session.post.assert_not_called()
    assert len(restarted.get_unsynced_timesheets(slot=3-slot)) == 1


@pytest.mark.parametrize('slot', [1, 2])
def test_normal_failure_requires_explicit_manual_retry(seeded, slot):
    db, row = seeded
    svc = service(db, slot)
    svc.session.post = Mock(return_value=reply(400, failed=[{'id': row, 'error_code': 140, 'reason': 'Employee not found'}]))
    assert svc.push_data()[2]['failed'] == 1
    assert not db.get_unsynced_timesheets(slot=slot)
    assert db.get_retry_queue()[0]["state"] == "failed"
    svc.push_data()
    assert svc.session.post.call_count == 1
    svc.session.post.return_value = reply(200, [row])
    assert svc.push_data(timesheet_ids=[row], manual_retry=True)[2]['success'] == 1
    assert not db.get_unsynced_timesheets(slot=slot)


@pytest.mark.parametrize('reason', ['Employee already exists', 'Unknown error', 'Duplicate employee code', ''])
def test_unrelated_errors_are_not_discarded(reason):
    assert not is_duplicate_error(140, reason)


@pytest.mark.parametrize('slot', [1, 2])
def test_401_waits_for_manual_retry_before_partial_success(seeded, slot):
    db, row = seeded
    svc = service(db, slot)
    svc.session.post = Mock(side_effect=[reply(401), reply(400, [row])])
    assert svc.push_data()[2]['failed'] == 1
    svc.push_data()
    assert svc.session.post.call_count == 1
    assert svc.push_data(timesheet_ids=[row], manual_retry=True)[2]['success'] == 1
    assert not db.get_retry_queue()


@pytest.mark.parametrize('reason', ['Duplicate record already exists', 'Time in range (5mins)'])
@pytest.mark.parametrize('slot', [1, 2])
def test_upgrade_suppresses_existing_duplicate_queue_before_first_upload(seeded, reason, slot):
    db, row = seeded
    db.mark_timesheet_sync_failed(row, reason, slot)
    upgraded = Database(str(db.db_path))
    assert not upgraded.get_unsynced_timesheets(slot=slot)
    assert upgraded.get_unsynced_timesheets(slot=3-slot)


def test_upgrade_keeps_unknown_errors_and_existing_success(seeded):
    db, row = seeded
    db.mark_timesheet_sync_failed(row, 'Bad request', 1)
    db.mark_timesheet_synced(row, 99, 2)
    upgraded = Database(str(db.db_path))
    assert not upgraded.get_unsynced_timesheets(slot=1)
    assert upgraded.get_retry_queue()[0]["state"] == "unconfirmed"
    assert upgraded.get_all_timesheets()[0]['backend_timesheet_id_2'] == 99


@pytest.mark.parametrize('synced_slot', [1, 2])
@pytest.mark.parametrize('by_date', [False, True])
def test_do_not_sync_blocks_the_remaining_destination(seeded, synced_slot, by_date):
    db, row = seeded
    db.mark_timesheet_synced(row, row, synced_slot)
    if by_date:
        assert db.set_timesheets_excluded_by_date_range('2026-08-24', '2026-08-24', True) == 1
    else:
        assert db.set_timesheets_excluded([row], True) == 1
    assert not db.get_unsynced_timesheets(slot=3-synced_slot)
    assert not db.get_unsynced_timesheets_by_ids([row], slot=3-synced_slot)
    db.set_timesheets_excluded([row], False)
    assert db.get_unsynced_timesheets(slot=3-synced_slot)
    assert not db.get_unsynced_timesheets(slot=synced_slot)


def test_stats_distinguish_duplicate_from_success_and_partial_delivery(seeded):
    db, row = seeded
    db.mark_timesheet_duplicate(row, 'Time in range (5mins)', 1)
    assert db.get_timesheet_stats()['pending'] == 1
    db.mark_timesheet_synced(row, row, 2)
    assert db.get_timesheet_stats() == {'total': 1, 'synced': 0, 'duplicates': 1,
                                      'excluded': 0, 'errors': 0, 'pending': 0}


def test_history_baseline_does_not_relabel_a_duplicate_as_uploaded(seeded):
    db, row = seeded
    db.mark_timesheet_duplicate(row, 'Duplicate record already exists', 2)
    assert db.baseline_slot_as_synced(2) == 0
    saved = db.get_all_timesheets()[0]
    assert saved['backend_timesheet_id_2'] is None
    assert saved['sync_skipped_reason_2']


def test_actual_success_clears_a_stale_skip_reason(seeded):
    db, row = seeded
    db.mark_timesheet_duplicate(row, 'Duplicate record already exists', 2)
    db.mark_timesheet_synced(row, 99, 2)
    saved = db.get_all_timesheets()[0]
    assert saved['backend_timesheet_id_2'] == 99
    assert saved['sync_skipped_reason_2'] is None


def test_overlapping_manual_and_scheduled_pushes_send_once_and_release_lock(seeded):
    db, row = seeded
    svc = service(db, 1)
    entered, release = threading.Event(), threading.Event()

    def post(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return reply(200, [row])

    svc.session.post = Mock(side_effect=post)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(svc.push_data)
        try:
            assert entered.wait(5)
            assert 'already running' in svc.push_data()[1]
        finally:
            release.set()
        assert first.result()[2]['success'] == 1
    assert svc.session.post.call_count == 1
    assert svc.push_data()[1] == 'No records to sync'
