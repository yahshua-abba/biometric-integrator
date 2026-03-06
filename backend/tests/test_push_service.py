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

    def test_push_batch_401_reauth_uses_string_token(self, mocker):
        """
        REGRESSION for Bug #1:
        When a 401 triggers re-authentication, the retry Authorization header
        must be 'Token <string>', NOT 'Token <dict>'.

        Before the fix, self.authenticate() returned the full dict and the
        header became: 'Token {'token': 'abc', 'user_logged': ...}'
        which is invalid and causes the retry to fail.
        """
        svc = make_service()

        # Capture a COPY of headers at call time — the dict is mutated in-place
        # between the first and second calls, so we can't rely on call_args_list
        # references pointing to the right state after the fact.
        captured_headers = []

        def capture_post(url, **kwargs):
            captured_headers.append(dict(kwargs.get('headers', {})))
            call_number = len(captured_headers)
            if call_number == 1:
                return mock_response(401, {'message': 'Token expired'})
            return mock_response(200, {'logs_successfully_sync': [1], 'logs_not_sync': []})

        mocker.patch.object(svc.session, 'post', side_effect=capture_post)

        mocker.patch.object(svc, 'authenticate', return_value={
            'token': 'fresh-token',
            'user_logged': 'Admin',
            'company_name': 'Test Co',
        })

        batch = [{'id': 1, 'employee': 'E001', 'log_time': '08:00', 'log_type': 'IN',
                  'sync_id': 'ZK_1_1_20260306080000', 'date': '2026-03-06'}]

        success, result = svc.push_batch('expired-token', batch)

        assert success is True
        assert len(captured_headers) == 2, "Expected 2 HTTP calls: initial + retry after 401"

        retry_auth = captured_headers[1].get('Authorization', '')

        # Must be 'Token fresh-token', NOT 'Token {'token': 'fresh-token', ...}'
        assert retry_auth == 'Token fresh-token', (
            f"Authorization header should be 'Token fresh-token' but got: {retry_auth!r}\n"
            "Bug #1 regression: authenticate() returns a dict — use auth_result['token'], not the dict."
        )

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
        db.mark_timesheet_synced.assert_called_once_with(1, 1)
        db.mark_timesheet_sync_failed.assert_called_once()
        failed_args = db.mark_timesheet_sync_failed.call_args[0]
        assert failed_args[0] == 2
