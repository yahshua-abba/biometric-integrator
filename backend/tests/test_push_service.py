"""
Regression tests for push_service.py

Run with:
    cd backend && python -m pytest tests/test_push_service.py -v
"""

import pytest
import sys
import os
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, patch, call
from services.push_service import PushService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_service(db=None):
    """Return a PushService with a mocked database."""
    db = db or MagicMock()
    db.get_api_config.return_value = {
        'push_url': 'https://yahshuapayroll.com/api',
        'push_username': 'testuser',
        'push_password': 'testpass',
        'push_token': None,
    }
    db.claim_delivery.side_effect = lambda ids, slot, manual: ids
    return PushService(db)


def mock_response(status_code, json_data):
    """Build a mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = str(json_data)
    return resp


# ---------------------------------------------------------------------------
# authenticate()
# ---------------------------------------------------------------------------

class TestAuthenticate:
    def test_authenticate_returns_dict_with_token(self, mocker):
        """authenticate() must return a dict — not a plain string token.

        This documents the contract that other callers depend on.
        Callers must use auth_result['token'], not the return value directly.
        """
        svc = make_service()
        mocker.patch.object(svc.session, 'post', return_value=mock_response(200, {
            'token': 'abc123',
            'user_logged': 'Admin User',
            'company_name': 'Test Company',
        }))

        result = svc.authenticate('testuser', 'testpass')

        assert isinstance(result, dict)
        assert result['token'] == 'abc123'
        assert result['user_logged'] == 'Admin User'
        assert result['company_name'] == 'Test Company'

    def test_authenticate_raises_on_missing_token(self, mocker):
        """authenticate() raises if the API responds 200 but has no token."""
        svc = make_service()
        mocker.patch.object(svc.session, 'post', return_value=mock_response(200, {}))

        with pytest.raises(Exception, match="No token"):
            svc.authenticate('testuser', 'testpass')

    def test_authenticate_raises_on_401(self, mocker):
        """authenticate() raises a clear error on bad credentials."""
        svc = make_service()
        mocker.patch.object(svc.session, 'post', return_value=mock_response(401, {
            'message': 'Invalid credentials'
        }))

        with pytest.raises(Exception, match="Login failed: Invalid credentials"):
            svc.authenticate('testuser', 'testpass')

    def test_authenticate_raises_on_connection_error(self, mocker):
        """authenticate() raises when the server is unreachable."""
        svc = make_service()
        mocker.patch.object(svc.session, 'post', side_effect=requests.exceptions.ConnectionError)

        with pytest.raises(Exception, match="Cannot connect"):
            svc.authenticate('testuser', 'testpass')


# ---------------------------------------------------------------------------
# push_batch() — REGRESSION for Bug #1
# ---------------------------------------------------------------------------

class TestPushBatch:
    def test_push_batch_success(self, mocker):
        """Happy path: 200 response returns (True, data)."""
        svc = make_service()
        batch = [{'id': 1, 'employee': 'E001', 'log_time': '08:00', 'log_type': 'IN',
                  'sync_id': 'ZK_1_1_20260306080000', 'date': '2026-03-06'}]

        mocker.patch.object(svc.session, 'post', return_value=mock_response(200, {
            'logs_successfully_sync': [1],
            'logs_not_sync': [],
        }))

        success, result = svc.push_batch('valid-token', batch)

        assert success is True
        assert result['logs_successfully_sync'] == [1]

    def test_push_batch_401_invalidates_token_without_automatic_resend(self, mocker):
        svc = make_service()
        post = mocker.patch.object(svc.session, 'post', return_value=mock_response(401, {}))
        auth = mocker.patch.object(svc, 'authenticate')
        success, result = svc.push_batch('expired', [{'id': 1}])
        assert not success and result['unconfirmed'] is False
        post.assert_called_once()
        auth.assert_not_called()
        svc.database.update_push_token.assert_called_once_with(None, slot=1)

    def test_push_batch_network_error_returns_failure(self, mocker):
        """Network errors yield (False, {'error': ...}) — they don't raise."""
        svc = make_service()
        mocker.patch.object(svc.session, 'post',
                            side_effect=requests.exceptions.ConnectionError)

        success, result = svc.push_batch('any-token', [{'id': 1}])

        assert success is False
        assert 'error' in result
        assert 'connect' in result['error'].lower()

    def test_push_batch_timeout_returns_failure(self, mocker):
        """Timeouts yield (False, {'error': ...}) — they don't raise."""
        svc = make_service()
        mocker.patch.object(svc.session, 'post',
                            side_effect=requests.exceptions.Timeout)

        success, result = svc.push_batch('any-token', [{'id': 1}])

        assert success is False
        assert 'error' in result
        assert 'timed out' in result['error'].lower()

    def test_push_batch_partial_success_on_400(self, mocker):
        """400 with some synced records is treated as partial success."""
        svc = make_service()
        mocker.patch.object(svc.session, 'post', return_value=mock_response(400, {
            'logs_successfully_sync': [1],
            'logs_not_sync': [{'id': 2, 'reason': 'Employee not found', 'error_code': 140}],
        }))

        success, result = svc.push_batch('token', [{'id': 1}, {'id': 2}])

        assert success is True
        assert 1 in result['logs_successfully_sync']


# ---------------------------------------------------------------------------
# push_data()
# ---------------------------------------------------------------------------

class TestPushData:
    def test_push_data_empty_queue_returns_early(self, mocker):
        """No unsynced records → success with 'No records to sync'."""
        db = MagicMock()
        db.get_api_config.return_value = {
            'push_url': 'https://yahshuapayroll.com/api',
            'push_username': 'u',
            'push_password': 'p',
            'push_token': 'valid-token',
        }
        db.get_push_token.return_value = 'valid-token'
        db.get_unsynced_timesheets.return_value = []
        db.create_sync_log.return_value = 1

        svc = make_service(db)
        success, message, stats = svc.push_data()

        assert success is True
        assert 'No records' in message
        assert stats['processed'] == 0
        db.update_push_token.assert_not_called()

    def test_push_data_skips_records_without_employee_code(self, mocker):
        """Records with no employee_code are counted as 'skipped', not 'failed'."""
        db = MagicMock()
        db.get_api_config.return_value = {
            'push_url': 'https://yahshuapayroll.com/api',
            'push_username': 'u',
            'push_password': 'p',
            'push_token': 'valid-token',
        }
        db.get_push_token.return_value = 'valid-token'
        db.get_unsynced_timesheets.return_value = [
            {'id': 1, 'employee_code': None, 'time': '08:00', 'log_type': 'in',
             'sync_id': 'ZK_1_1_20260306', 'date': '2026-03-06', 'branch_id': None},
        ]
        db.create_sync_log.return_value = 1

        svc = make_service(db)
        success, message, stats = svc.push_data()

        assert stats['skipped'] == 1
        assert stats['failed'] == 0

    def test_push_data_increments_success_and_failed_correctly(self, mocker):
        """Synced IDs from API response are marked synced; failed ones are marked failed."""
        db = MagicMock()
        db.get_api_config.return_value = {
            'push_url': 'https://yahshuapayroll.com/api',
            'push_username': 'u',
            'push_password': 'p',
            'push_token': 'valid-token',
        }
        db.get_push_token.return_value = 'valid-token'
        db.get_unsynced_timesheets.return_value = [
            {'id': 1, 'employee_code': 'E001', 'time': '08:00', 'log_type': 'in',
             'sync_id': 'ZK_1_1_20260306080000', 'date': '2026-03-06', 'branch_id': None},
            {'id': 2, 'employee_code': 'E002', 'time': '09:00', 'log_type': 'out',
             'sync_id': 'ZK_1_2_20260306090000', 'date': '2026-03-06', 'branch_id': None},
        ]
        db.create_sync_log.return_value = 1

        svc = make_service(db)
        mocker.patch.object(svc, 'push_batch', return_value=(True, {
            'logs_successfully_sync': [1],
            'logs_not_sync': [{'id': 2, 'reason': 'Employee not found', 'error_code': 140}],
        }))

        success, message, stats = svc.push_data()

        assert stats['success'] == 1
        assert stats['failed'] == 1
        db.mark_timesheet_synced.assert_called_once_with(1, 1, slot=1)
        db.mark_timesheet_sync_failed.assert_called_once()
        failed_args = db.mark_timesheet_sync_failed.call_args[0]
        assert failed_args[0] == 2


# ---------------------------------------------------------------------------
# Whole-batch rejections (LCG, Oct 2026: one employee code matched two employees,
# Payroll answered with a bare string, and every later batch was never sent)
# ---------------------------------------------------------------------------

DUPLICATE_EMPLOYEE = "get() returned more than one Employee -- it returned 2!"


def make_queue(ids):
    db = MagicMock()
    db.get_push_token.return_value = 'valid-token'
    db.create_sync_log.return_value = 1
    db.get_unsynced_timesheets.return_value = [
        {'id': i, 'employee_code': f'E{i}', 'time': '08:00', 'log_type': 'in',
         'sync_id': f'ZK_1_{i}_20261007080000', 'date': '2026-10-07', 'branch_id': None}
        for i in ids
    ]
    return make_service(db), db


class TestRejectedBatch:
    def test_push_batch_plain_string_400_is_a_readable_rejection(self, mocker):
        svc = make_service()
        mocker.patch.object(svc.session, 'post', return_value=mock_response(400, DUPLICATE_EMPLOYEE))

        success, result = svc.push_batch('token', [{'id': 1}])

        assert success is False
        assert result['rejected'] is True and result['unconfirmed'] is False
        assert 'More than one employee' in result['error']

    def test_push_batch_plain_string_200_is_unconfirmed_not_a_crash(self, mocker):
        svc = make_service()
        mocker.patch.object(svc.session, 'post', return_value=mock_response(200, 'OK'))

        success, result = svc.push_batch('token', [{'id': 1}])

        assert success is False
        assert result['unconfirmed'] is True and not result.get('rejected')

    def test_rejected_batch_is_resent_singly_and_later_batches_still_go(self, mocker):
        """One bad employee fails alone; the rest of its batch and the next batch sync."""
        svc, db = make_queue(range(1, 53))  # batches of 50 + 2

        def payroll(token, log_list):
            ids = [r['id'] for r in log_list]
            if 7 in ids and len(ids) > 1:
                return False, {'error': 'More than one employee', 'unconfirmed': False, 'rejected': True}
            if ids == [7]:
                return False, {'error': 'More than one employee', 'unconfirmed': False, 'rejected': True}
            return True, {'logs_successfully_sync': ids, 'logs_not_sync': []}

        push = mocker.patch.object(svc, 'push_batch', side_effect=payroll)

        success, message, stats = svc.push_data()

        assert success is True
        assert stats['success'] == 51 and stats['failed'] == 1
        assert push.call_count == 1 + 50 + 1
        db.mark_timesheet_sync_failed.assert_called_once_with(7, 'More than one employee', slot=1)

    def test_single_record_rejection_does_not_stop_the_run(self, mocker):
        svc, db = make_queue(range(1, 52))  # batch 2 holds only record 51

        def payroll(token, log_list):
            ids = [r['id'] for r in log_list]
            if ids == [51]:
                return False, {'error': 'Bad employee', 'unconfirmed': False, 'rejected': True}
            return True, {'logs_successfully_sync': ids, 'logs_not_sync': []}

        mocker.patch.object(svc, 'push_batch', side_effect=payroll)
        success, message, stats = svc.push_data()

        assert success is True
        assert stats['success'] == 50 and stats['failed'] == 1
        assert stats['batches_completed'] == 2

    def test_connection_loss_during_resend_stops_and_requeues_the_unsent_rest(self, mocker):
        svc, db = make_queue([1, 2, 3])
        responses = iter([
            (False, {'error': 'rejected', 'unconfirmed': False, 'rejected': True}),
            (True, {'logs_successfully_sync': [1], 'logs_not_sync': []}),
            (False, {'error': 'Cannot connect', 'unconfirmed': True}),
        ])
        mocker.patch.object(svc, 'push_batch', side_effect=lambda t, l: next(responses))

        success, message, stats = svc.push_data()

        assert success is False and 'Cannot connect' in message
        assert stats['success'] == 1 and stats['failed'] == 1
        # Record 2 was on the wire when the connection dropped; record 3 never left.
        db.mark_timesheet_sync_failed.assert_called_once_with(2, 'Cannot connect', slot=1, unconfirmed=True)
        db.release_delivery.assert_called_once_with([3], 1, 'Cannot connect', {})


class TestExpiredLogin:
    def test_expired_login_logs_in_again_and_resends_once(self, mocker):
        svc, db = make_queue([1])
        responses = iter([
            (False, {'error': 'Authentication expired', 'unconfirmed': False, 'not_sent': True, 'auth_expired': True}),
            (True, {'logs_successfully_sync': [1], 'logs_not_sync': []}),
        ])
        push = mocker.patch.object(svc, 'push_batch', side_effect=lambda t, l: next(responses))
        mocker.patch.object(svc, 'authenticate', return_value={'token': 'fresh-token'})

        success, message, stats = svc.push_data()

        assert success is True and stats['success'] == 1
        assert [c.args[0] for c in push.call_args_list] == ['valid-token', 'fresh-token']
        db.release_delivery.assert_not_called()

    def test_push_batch_flags_an_expired_login(self, mocker):
        svc = make_service()
        mocker.patch.object(svc.session, 'post', return_value=mock_response(401, {}))
        success, result = svc.push_batch('expired', [{'id': 1}])
        assert not success and result['not_sent'] and result['auth_expired']
