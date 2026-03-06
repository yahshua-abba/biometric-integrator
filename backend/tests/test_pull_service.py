"""
Regression tests for pull_service.py

Run with:
    cd backend && python -m pytest tests/test_pull_service.py -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, patch
from datetime import datetime
from services.pull_service import PullService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_service():
    """Return a PullService with a fully mocked database."""
    db = MagicMock()
    db.get_device.return_value = {'id': 1, 'name': 'zkteko', 'ip': '192.168.1.201',
                                   'port': 4370, 'comm_key': 0}
    db.get_enabled_devices.return_value = [
        {'id': 1, 'name': 'zkteko', 'ip': '192.168.1.201', 'port': 4370, 'comm_key': 0}
    ]
    db.create_sync_log.return_value = 1
    db.get_employee_by_code.return_value = {'id': 10, 'name': 'Test User', 'employee_code': '1'}
    db.add_timesheet_entry.return_value = 1  # new record
    return PullService(db)


def make_log(user_id, timestamp, punch=0):
    """Create a mock ZKTeco attendance log object."""
    log = MagicMock()
    log.user_id = user_id
    log.timestamp = timestamp
    log.punch = punch
    return log


def make_user(user_id, name):
    """Create a mock ZKTeco user object."""
    u = MagicMock()
    u.user_id = user_id
    u.name = name
    return u


# ---------------------------------------------------------------------------
# Date filtering — REGRESSION for Bug #3
# ---------------------------------------------------------------------------

class TestDateFiltering:
    def test_filtered_increments_for_records_outside_date_range(self, mocker):
        """
        REGRESSION for Bug #3:
        Records outside the requested date range must increment stats['filtered'],
        NOT silently disappear. Before the fix, the count of total_logs and the
        sum of new+duplicates+errors never matched.
        """
        svc = make_service()

        inside = make_log(1, datetime(2026, 3, 6, 8, 0, 0))   # within range
        outside = make_log(2, datetime(2026, 3, 4, 8, 0, 0))  # before range

        mock_conn = MagicMock()
        mock_conn.get_attendance.return_value = [inside, outside]
        mock_conn.get_users.return_value = [make_user(1, 'Alice'), make_user(2, 'Bob')]
        mocker.patch.object(svc, 'connect', return_value=mock_conn)
        mocker.patch.object(svc, 'disconnect')

        _, _, stats = svc._pull_from_device(1, '2026-03-05', '2026-03-06')

        assert stats['filtered'] == 1, (
            "Bug #3 regression: records outside date range must increment stats['filtered'].\n"
            f"Got stats['filtered'] = {stats['filtered']}, expected 1."
        )
        assert stats['processed'] == 1
        assert stats['total_logs'] == 2

    def test_stats_sum_equals_total_logs(self, mocker):
        """
        processed + filtered == total_logs always.
        (processed itself equals new_records + duplicates + errors.)
        """
        svc = make_service()

        logs = [
            make_log(1, datetime(2026, 3, 6, 8, 0, 0)),   # in range
            make_log(2, datetime(2026, 3, 6, 9, 0, 0)),   # in range
            make_log(3, datetime(2026, 3, 1, 8, 0, 0)),   # outside range (filtered)
            make_log(4, datetime(2026, 2, 28, 8, 0, 0)),  # outside range (filtered)
        ]

        # User 2 has no employee record → will be created
        svc.database.get_employee_by_code.side_effect = lambda code: (
            {'id': 10, 'name': 'Alice', 'employee_code': code} if code == '1' else None
        )
        svc.database.add_or_update_employee.return_value = 20
        svc.database.get_employee_by_code.side_effect = lambda code: (
            {'id': int(code) * 10, 'name': f'User {code}', 'employee_code': code}
        )

        mock_conn = MagicMock()
        mock_conn.get_attendance.return_value = logs
        mock_conn.get_users.return_value = [make_user(i+1, f'User {i+1}') for i in range(4)]
        mocker.patch.object(svc, 'connect', return_value=mock_conn)
        mocker.patch.object(svc, 'disconnect')

        _, _, stats = svc._pull_from_device(1, '2026-03-05', '2026-03-06')

        assert stats['total_logs'] == 4
        assert stats['processed'] + stats['filtered'] == stats['total_logs'], (
            f"Accounting mismatch: processed({stats['processed']}) + "
            f"filtered({stats['filtered']}) != total_logs({stats['total_logs']})"
        )

    def test_completion_message_includes_filtered_count(self, mocker):
        """The pull completion message reports how many records were outside the date range."""
        svc = make_service()

        inside = make_log(1, datetime(2026, 3, 6, 8, 0, 0))
        outside = make_log(2, datetime(2026, 2, 1, 8, 0, 0))

        mock_conn = MagicMock()
        mock_conn.get_attendance.return_value = [inside, outside]
        mock_conn.get_users.return_value = [make_user(1, 'Alice'), make_user(2, 'Bob')]
        mocker.patch.object(svc, 'connect', return_value=mock_conn)
        mocker.patch.object(svc, 'disconnect')

        _, message, _ = svc._pull_from_device(1, '2026-03-05', '2026-03-06')

        assert 'outside date range' in message, (
            f"Expected 'outside date range' in message but got: {message!r}"
        )


# ---------------------------------------------------------------------------
# Punch type mapping
# ---------------------------------------------------------------------------

class TestPunchTypeMapping:
    @pytest.mark.parametrize("punch", [0, 3, 4])
    def test_punch_in_types(self, mocker, punch):
        """Punch types 0, 3, 4 map to log_type='in'."""
        svc = make_service()

        log = make_log(1, datetime(2026, 3, 6, 8, 0, 0), punch=punch)
        mock_conn = MagicMock()
        mock_conn.get_attendance.return_value = [log]
        mock_conn.get_users.return_value = [make_user(1, 'Alice')]
        mocker.patch.object(svc, 'connect', return_value=mock_conn)
        mocker.patch.object(svc, 'disconnect')

        svc._pull_from_device(1, '2026-03-06', '2026-03-06')

        call_kwargs = svc.database.add_timesheet_entry.call_args
        assert call_kwargs.kwargs['log_type'] == 'in', (
            f"Punch type {punch} should map to 'in', got '{call_kwargs.kwargs['log_type']}'"
        )

    @pytest.mark.parametrize("punch", [1, 2, 5])
    def test_punch_out_types(self, mocker, punch):
        """Punch types 1, 2, 5 map to log_type='out'."""
        svc = make_service()

        log = make_log(1, datetime(2026, 3, 6, 17, 0, 0), punch=punch)
        mock_conn = MagicMock()
        mock_conn.get_attendance.return_value = [log]
        mock_conn.get_users.return_value = [make_user(1, 'Alice')]
        mocker.patch.object(svc, 'connect', return_value=mock_conn)
        mocker.patch.object(svc, 'disconnect')

        svc._pull_from_device(1, '2026-03-06', '2026-03-06')

        call_kwargs = svc.database.add_timesheet_entry.call_args
        assert call_kwargs.kwargs['log_type'] == 'out', (
            f"Punch type {punch} should map to 'out', got '{call_kwargs.kwargs['log_type']}'"
        )


# ---------------------------------------------------------------------------
# Employee auto-creation
# ---------------------------------------------------------------------------

class TestEmployeeHandling:
    def test_pull_creates_employee_if_not_in_db(self, mocker):
        """A device user not in the DB is created automatically during pull."""
        svc = make_service()

        # No employee record exists initially
        svc.database.get_employee_by_code.side_effect = [
            None,  # first lookup: not found
            {'id': 99, 'name': 'New User', 'employee_code': '42'},  # after creation
        ]

        log = make_log(42, datetime(2026, 3, 6, 8, 0, 0))
        mock_conn = MagicMock()
        mock_conn.get_attendance.return_value = [log]
        mock_conn.get_users.return_value = [make_user(42, 'New User')]
        mocker.patch.object(svc, 'connect', return_value=mock_conn)
        mocker.patch.object(svc, 'disconnect')

        _, _, stats = svc._pull_from_device(1, '2026-03-06', '2026-03-06')

        svc.database.add_or_update_employee.assert_called()
        assert stats['new_records'] == 1

    def test_pull_duplicate_entry_increments_duplicates(self, mocker):
        """add_timesheet_entry returning None (duplicate sync_id) increments duplicates."""
        svc = make_service()
        svc.database.add_timesheet_entry.return_value = None  # duplicate

        log = make_log(1, datetime(2026, 3, 6, 8, 0, 0))
        mock_conn = MagicMock()
        mock_conn.get_attendance.return_value = [log]
        mock_conn.get_users.return_value = [make_user(1, 'Alice')]
        mocker.patch.object(svc, 'connect', return_value=mock_conn)
        mocker.patch.object(svc, 'disconnect')

        _, _, stats = svc._pull_from_device(1, '2026-03-06', '2026-03-06')

        assert stats['duplicates'] == 1
        assert stats['new_records'] == 0
