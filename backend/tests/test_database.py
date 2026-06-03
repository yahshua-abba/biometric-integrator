"""
Regression tests for database.py — especially soft-delete and duplicate-sync prevention.

Run with:
    cd backend && python -m pytest tests/test_database.py -v
"""

import sys
import os
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database


@pytest.fixture
def db(tmp_path):
    """In-memory Database backed by a temporary file."""
    return Database(db_path=str(tmp_path / "test.db"))


def _seed_employee(db, backend_id=1):
    db.add_or_update_employee(backend_id=str(backend_id), name="Test User",
                              employee_code=str(backend_id))
    emp = db.get_employee_by_code(str(backend_id))
    return emp["id"]


# ---------------------------------------------------------------------------
# clearTimesheets — soft-delete behaviour
# ---------------------------------------------------------------------------

class TestClearTimesheetsSoftDelete:
    def test_synced_record_is_soft_deleted_not_removed(self, db):
        """clearTimesheets(only_synced=True) must NOT hard-delete synced rows."""
        emp_id = _seed_employee(db)

        ts_id = db.add_timesheet_entry(
            sync_id="ZK_1_1_20260601080000",
            employee_id=emp_id,
            log_type="in",
            date="2026-06-01",
            time="08:00:00",
            device_id=None,
        )
        # Mark as synced
        db.mark_timesheet_synced(ts_id, backend_timesheet_id=999)

        # Simulate what bridge.clearTimesheets does (only_synced=True)
        import sqlite3
        from datetime import datetime
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE timesheet SET deleted_at = ?
            WHERE date >= ? AND date <= ?
            AND backend_timesheet_id IS NOT NULL
            AND deleted_at IS NULL
        """, (datetime.now(), "2026-06-01", "2026-06-01"))
        conn.commit()
        conn.close()

        # Row must still exist in DB
        row = db.get_timesheet_by_sync_id("ZK_1_1_20260601080000")
        assert row is not None, "Soft-deleted row should still exist in DB"
        assert row["deleted_at"] is not None, "deleted_at must be set after soft-delete"

    def test_soft_deleted_records_hidden_from_get_all_timesheets(self, db):
        emp_id = _seed_employee(db)

        ts_id = db.add_timesheet_entry(
            sync_id="ZK_1_1_20260601080000",
            employee_id=emp_id,
            log_type="in",
            date="2026-06-01",
            time="08:00:00",
            device_id=None,
        )
        db.mark_timesheet_synced(ts_id, backend_timesheet_id=999)

        from datetime import datetime
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE timesheet SET deleted_at = ? WHERE id = ?", (datetime.now(), ts_id))
        conn.commit()
        conn.close()

        timesheets = db.get_all_timesheets()
        assert not any(t["sync_id"] == "ZK_1_1_20260601080000" for t in timesheets), \
            "Soft-deleted record must not appear in get_all_timesheets()"

    def test_soft_deleted_records_hidden_from_get_unsynced_timesheets(self, db):
        emp_id = _seed_employee(db)

        # Insert an UNSYNCED record, then soft-delete it
        ts_id = db.add_timesheet_entry(
            sync_id="ZK_1_1_20260601090000",
            employee_id=emp_id,
            log_type="out",
            date="2026-06-01",
            time="09:00:00",
            device_id=None,
        )

        from datetime import datetime
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE timesheet SET deleted_at = ? WHERE id = ?", (datetime.now(), ts_id))
        conn.commit()
        conn.close()

        unsynced = db.get_unsynced_timesheets(limit=100)
        assert not any(t["sync_id"] == "ZK_1_1_20260601090000" for t in unsynced), \
            "Soft-deleted record must not appear in get_unsynced_timesheets()"

    def test_stats_exclude_soft_deleted_records(self, db):
        emp_id = _seed_employee(db)

        ts_id = db.add_timesheet_entry(
            sync_id="ZK_1_1_20260601080000",
            employee_id=emp_id,
            log_type="in",
            date="2026-06-01",
            time="08:00:00",
            device_id=None,
        )
        db.mark_timesheet_synced(ts_id, backend_timesheet_id=999)

        stats_before = db.get_timesheet_stats()
        assert stats_before["total"] == 1

        from datetime import datetime
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE timesheet SET deleted_at = ? WHERE id = ?", (datetime.now(), ts_id))
        conn.commit()
        conn.close()

        stats_after = db.get_timesheet_stats()
        assert stats_after["total"] == 0, \
            "Soft-deleted records must not be counted in get_timesheet_stats()"


# ---------------------------------------------------------------------------
# Re-pull after clear — REGRESSION for duplicate-sync bug
# ---------------------------------------------------------------------------

class TestDuplicateSyncPrevention:
    def test_repull_after_clear_returns_none_from_add_timesheet_entry(self, db):
        """
        REGRESSION: After a synced record is soft-deleted (simulating clearTimesheets),
        re-inserting the same sync_id (simulating a re-pull from the device) must
        return None so the pull service counts it as a duplicate and does NOT push it.

        Scenario:
          1. Record pulled from biometrics and pushed to YP (synced).
          2. User calls clearTimesheets → synced record is soft-deleted.
          3. User re-pulls from device → same sync_id is seen again.
          4. add_timesheet_entry must return None (UNIQUE constraint hit).
          5. Push query must NOT include this record.
        """
        emp_id = _seed_employee(db)
        sync_id = "ZK_1_1_20260601080000"

        # Step 1: Pull and sync
        ts_id = db.add_timesheet_entry(
            sync_id=sync_id,
            employee_id=emp_id,
            log_type="in",
            date="2026-06-01",
            time="08:00:00",
            device_id=None,
        )
        assert ts_id is not None
        db.mark_timesheet_synced(ts_id, backend_timesheet_id=42)

        # Step 2: Soft-delete (clearTimesheets)
        from datetime import datetime
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE timesheet SET deleted_at = ?
            WHERE id = ? AND backend_timesheet_id IS NOT NULL
        """, (datetime.now(), ts_id))
        conn.commit()
        conn.close()

        # Step 3 & 4: Re-pull — same sync_id must be rejected
        result = db.add_timesheet_entry(
            sync_id=sync_id,
            employee_id=emp_id,
            log_type="in",
            date="2026-06-01",
            time="08:00:00",
            device_id=None,
        )
        assert result is None, (
            "Re-inserting a sync_id that was previously synced (even after soft-delete) "
            "must return None to prevent a duplicate push."
        )

    def test_repull_after_clear_does_not_appear_in_unsynced_queue(self, db):
        """
        After the re-pull attempt, the record must not appear in the push queue.
        """
        emp_id = _seed_employee(db)
        sync_id = "ZK_1_1_20260601080000"

        ts_id = db.add_timesheet_entry(
            sync_id=sync_id, employee_id=emp_id, log_type="in",
            date="2026-06-01", time="08:00:00", device_id=None,
        )
        db.mark_timesheet_synced(ts_id, backend_timesheet_id=42)

        from datetime import datetime
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE timesheet SET deleted_at = ? WHERE id = ?", (datetime.now(), ts_id))
        conn.commit()
        conn.close()

        # Attempt re-insert (simulates re-pull); returns None but has no effect
        db.add_timesheet_entry(
            sync_id=sync_id, employee_id=emp_id, log_type="in",
            date="2026-06-01", time="08:00:00", device_id=None,
        )

        unsynced = db.get_unsynced_timesheets(limit=100)
        assert not any(t["sync_id"] == sync_id for t in unsynced), \
            "A previously-synced record must never re-enter the push queue after re-pull."

    def test_unsynced_record_soft_deleted_cannot_be_repulled(self, db):
        """
        REGRESSION: Unsynced records that are soft-deleted must NOT reappear on
        a re-pull from the biometric device. Once deleted, they stay gone.

        Scenario:
          1. Logs pulled from device → stored in SQLite (unsynced).
          2. User deletes them via clearTimesheets (now soft-delete).
          3. User pulls again → device still has those logs.
          4. add_timesheet_entry must return None (UNIQUE constraint hit).
          5. Records must not appear in unsynced queue or push again.
        """
        emp_id = _seed_employee(db)
        sync_id = "ZK_1_1_20260601100000"

        # Step 1: Pull — unsynced record
        ts_id = db.add_timesheet_entry(
            sync_id=sync_id, employee_id=emp_id, log_type="in",
            date="2026-06-01", time="10:00:00", device_id=None,
        )
        assert ts_id is not None

        # Step 2: Soft-delete (clearTimesheets only_synced=False path)
        from datetime import datetime
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE timesheet SET deleted_at = ? WHERE id = ?", (datetime.now(), ts_id))
        conn.commit()
        conn.close()

        # Step 3 & 4: Re-pull — must be blocked
        result = db.add_timesheet_entry(
            sync_id=sync_id, employee_id=emp_id, log_type="in",
            date="2026-06-01", time="10:00:00", device_id=None,
        )
        assert result is None, \
            "A soft-deleted unsynced record must not be re-insertable on re-pull."

        # Step 5: Must not appear in push queue
        unsynced = db.get_unsynced_timesheets(limit=100)
        assert not any(t["sync_id"] == sync_id for t in unsynced), \
            "A soft-deleted unsynced record must not appear in the push queue."
