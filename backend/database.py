"""
Biometric Integration - Database Manager
SQLite database for storing timesheet data and sync status
"""

import sqlite3
import json
import sys
import os
from datetime import datetime
from pathlib import Path
import logging
from services.sync_errors import is_duplicate_error

logger = logging.getLogger(__name__)

# Determine if running as frozen executable
IS_FROZEN = getattr(sys, 'frozen', False)


def _slot_cols(slot):
    """Return (backend_id, synced_at, error) timesheet column names for a push slot.

    Slot 1 is the primary/original destination; slot 2 is the optional second
    push config. Column names are internal constants (never user input).
    """
    if int(slot) == 2:
        return 'backend_timesheet_id_2', 'synced_at_2', 'sync_error_message_2'
    return 'backend_timesheet_id', 'synced_at', 'sync_error_message'


def _token_cols(slot):
    """Return (token, token_created_at, user_logged) api_config column names for a slot."""
    if int(slot) == 2:
        return 'push_token_2', 'push_token_created_at_2', 'push_user_logged_2'
    return 'push_token', 'push_token_created_at', 'push_user_logged'

def get_app_data_dir():
    """Get persistent app data directory based on platform"""
    if IS_FROZEN:
        # Use platform-specific app data directory for packaged app
        if sys.platform == 'win32':
            # Windows: C:\Users\<user>\AppData\Local\ZKTecoIntegration
            base = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
            return os.path.join(base, 'ZKTecoIntegration')
        elif sys.platform == 'darwin':
            # macOS: ~/Library/Application Support/ZKTecoIntegration
            return os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'ZKTecoIntegration')
        else:
            # Linux: ~/.local/share/ZKTecoIntegration
            return os.path.join(os.path.expanduser('~'), '.local', 'share', 'ZKTecoIntegration')
    else:
        # Development: use local database folder
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database')

class Database:
    def __init__(self, db_path=None):
        """Initialize database connection and create tables if needed"""
        if db_path:
            self.db_path = Path(db_path)
        else:
            app_data_dir = get_app_data_dir()
            os.makedirs(app_data_dir, exist_ok=True)
            self.db_path = Path(app_data_dir) / 'zkteco_integration.db'

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Database path: {self.db_path}")
        self.init_database()

    def get_connection(self):
        """Get database connection with row factory"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """Create all tables and indexes"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Company table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS company (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backend_id INTEGER UNIQUE,
                    name TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_backend_id ON company(backend_id)")

            # Employee table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS employee (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backend_id INTEGER UNIQUE,
                    name TEXT NOT NULL,
                    employee_code TEXT,
                    employee_number INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    deleted_at DATETIME
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_employee_backend_id ON employee(backend_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_employee_code ON employee(employee_code)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_employee_deleted_at ON employee(deleted_at)")

            # Timesheet table (primary sync table)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS timesheet (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sync_id TEXT UNIQUE NOT NULL,
                    employee_id INTEGER NOT NULL,
                    log_type TEXT NOT NULL CHECK(log_type IN ('in', 'out')),
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    photo_path TEXT,
                    is_synced BOOLEAN DEFAULT 0,
                    status TEXT DEFAULT 'success',
                    error_message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    backend_timesheet_id INTEGER,
                    synced_at DATETIME,
                    sync_error_message TEXT,
                    FOREIGN KEY (employee_id) REFERENCES employee(id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timesheet_sync_id ON timesheet(sync_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timesheet_employee_id ON timesheet(employee_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timesheet_date ON timesheet(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timesheet_is_synced ON timesheet(is_synced)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timesheet_backend_id ON timesheet(backend_timesheet_id)")

            # Users table (admin access)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    email TEXT NOT NULL,
                    name TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    last_login DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Sync logs table (track pull/push/config/other operations)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sync_type TEXT NOT NULL CHECK(sync_type IN ('pull', 'push', 'config', 'other')),
                    status TEXT NOT NULL CHECK(status IN ('started', 'success', 'error')),
                    records_processed INTEGER DEFAULT 0,
                    records_success INTEGER DEFAULT 0,
                    records_failed INTEGER DEFAULT 0,
                    error_message TEXT,
                    started_at DATETIME NOT NULL,
                    completed_at DATETIME,
                    metadata TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_logs_type ON sync_logs(sync_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_logs_status ON sync_logs(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_logs_started ON sync_logs(started_at)")

            # Device table (for multi-device support)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS device (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    ip TEXT NOT NULL,
                    port INTEGER DEFAULT 4370,
                    comm_key INTEGER DEFAULT 0,
                    branch_id TEXT,
                    enabled BOOLEAN DEFAULT 1,
                    last_pull_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    deleted_at DATETIME
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_device_enabled ON device(enabled)")
            # Note: idx_device_deleted_at and idx_device_unique_ip_active are created after migration adds deleted_at column

            # API configuration table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    device_ip TEXT,
                    device_port INTEGER DEFAULT 4370,
                    push_url TEXT,
                    push_auth_type TEXT,
                    push_credentials TEXT,
                    push_username TEXT,
                    push_password TEXT,
                    push_token TEXT,
                    push_token_created_at DATETIME,
                    pull_interval_minutes INTEGER DEFAULT 30,
                    push_interval_minutes INTEGER DEFAULT 15,
                    last_pull_at DATETIME,
                    last_push_at DATETIME,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Add new columns to existing table if they don't exist (for migration)
            # Device config fields
            try:
                cursor.execute("ALTER TABLE api_config ADD COLUMN device_ip TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE api_config ADD COLUMN device_port INTEGER DEFAULT 4370")
            except:
                pass
            # YAHSHUA push credential fields
            try:
                cursor.execute("ALTER TABLE api_config ADD COLUMN push_username TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE api_config ADD COLUMN push_password TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE api_config ADD COLUMN push_token TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE api_config ADD COLUMN push_token_created_at DATETIME")
            except:
                pass
            # YAHSHUA user info from login response
            try:
                cursor.execute("ALTER TABLE api_config ADD COLUMN push_user_logged TEXT")
            except:
                pass

            # Second push destination (Config 2) - optional, enabled via push_enabled_2.
            # Mirrors the primary push_* columns so a copy of every log can be sent
            # to a second payroll system simultaneously.
            for stmt in (
                "ALTER TABLE api_config ADD COLUMN push_url_2 TEXT",
                "ALTER TABLE api_config ADD COLUMN push_username_2 TEXT",
                "ALTER TABLE api_config ADD COLUMN push_password_2 TEXT",
                "ALTER TABLE api_config ADD COLUMN push_token_2 TEXT",
                "ALTER TABLE api_config ADD COLUMN push_token_created_at_2 DATETIME",
                "ALTER TABLE api_config ADD COLUMN push_user_logged_2 TEXT",
                "ALTER TABLE api_config ADD COLUMN push_enabled_2 BOOLEAN DEFAULT 0",
            ):
                try:
                    cursor.execute(stmt)
                except:
                    pass

            # Migration: Update sync_logs table to allow 'other' sync_type
            # Check if we need to migrate by trying to insert and rollback
            try:
                cursor.execute("INSERT INTO sync_logs (sync_type, status, started_at) VALUES ('other', 'success', datetime('now'))")
                # If it works, delete the test record
                cursor.execute("DELETE FROM sync_logs WHERE sync_type = 'other' AND rowid = last_insert_rowid()")
            except sqlite3.IntegrityError:
                # Need to migrate - recreate table with new constraint
                logger.info("Migrating sync_logs table to support 'other' sync_type")
                cursor.execute("ALTER TABLE sync_logs RENAME TO sync_logs_old")
                cursor.execute("""
                    CREATE TABLE sync_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sync_type TEXT NOT NULL CHECK(sync_type IN ('pull', 'push', 'config', 'other')),
                        status TEXT NOT NULL CHECK(status IN ('started', 'success', 'error')),
                        records_processed INTEGER DEFAULT 0,
                        records_success INTEGER DEFAULT 0,
                        records_failed INTEGER DEFAULT 0,
                        error_message TEXT,
                        started_at DATETIME NOT NULL,
                        completed_at DATETIME,
                        metadata TEXT
                    )
                """)
                cursor.execute("""
                    INSERT INTO sync_logs (id, sync_type, status, records_processed, records_success,
                        records_failed, error_message, started_at, completed_at, metadata)
                    SELECT id, sync_type, status, records_processed, records_success,
                        records_failed, error_message, started_at, completed_at, metadata
                    FROM sync_logs_old
                """)
                cursor.execute("DROP TABLE sync_logs_old")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_logs_type ON sync_logs(sync_type)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_logs_status ON sync_logs(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_logs_started ON sync_logs(started_at)")
                logger.info("sync_logs table migration completed")

            # Insert default config if not exists
            cursor.execute("SELECT COUNT(*) as count FROM api_config WHERE id = 1")
            if cursor.fetchone()['count'] == 0:
                cursor.execute("""
                    INSERT INTO api_config (id, pull_interval_minutes, push_interval_minutes)
                    VALUES (1, 30, 15)
                """)

            # Add device_id column to timesheet table (for multi-device support)
            try:
                cursor.execute("ALTER TABLE timesheet ADD COLUMN device_id INTEGER REFERENCES device(id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_timesheet_device_id ON timesheet(device_id)")
            except:
                pass

            # Add deleted_at column to device table (for soft delete)
            try:
                cursor.execute("ALTER TABLE device ADD COLUMN deleted_at DATETIME")
            except:
                pass  # Column already exists

            # Add comm_key column to device table (for device communication password)
            try:
                cursor.execute("ALTER TABLE device ADD COLUMN comm_key INTEGER DEFAULT 0")
            except:
                pass  # Column already exists

            # Add branch_id column to device table (for YAHSHUA branch association)
            try:
                cursor.execute("ALTER TABLE device ADD COLUMN branch_id TEXT")
            except:
                pass  # Column already exists

            # Add excluded_from_sync column to timesheet (user-marked "do not sync")
            try:
                cursor.execute("ALTER TABLE timesheet ADD COLUMN excluded_from_sync BOOLEAN DEFAULT 0")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_timesheet_excluded ON timesheet(excluded_from_sync)")
            except:
                pass  # Column already exists

            # Add deleted_at to timesheet for soft-delete (preserves sync_id history to prevent re-push)
            try:
                cursor.execute("ALTER TABLE timesheet ADD COLUMN deleted_at DATETIME")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_timesheet_deleted_at ON timesheet(deleted_at)")
            except:
                pass  # Column already exists

            # Per-destination sync status for the second push config (Config 2).
            # Independent of the primary columns so a record can be synced to
            # Config 1 while still pending/failed for Config 2 (and vice versa).
            try:
                cursor.execute("ALTER TABLE timesheet ADD COLUMN backend_timesheet_id_2 INTEGER")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_timesheet_backend_id_2 ON timesheet(backend_timesheet_id_2)")
            except:
                pass  # Column already exists
            try:
                cursor.execute("ALTER TABLE timesheet ADD COLUMN synced_at_2 DATETIME")
            except:
                pass  # Column already exists
            try:
                cursor.execute("ALTER TABLE timesheet ADD COLUMN sync_error_message_2 TEXT")
            except:
                pass  # Column already exists

            # Create indexes for deleted_at (after column exists)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_device_deleted_at ON device(deleted_at)")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_device_unique_ip_active ON device(ip) WHERE deleted_at IS NULL")

            # A duplicate is terminal for its destination, but is not a successful upload.
            for column in ('sync_skipped_reason', 'sync_skipped_reason_2'):
                if column not in {row[1] for row in cursor.execute('PRAGMA table_info(timesheet)')}:
                    cursor.execute(f'ALTER TABLE timesheet ADD COLUMN {column} TEXT')
            # Preserve known duplicate rejections from older builds before the scheduler starts.
            for suffix in ('', '_2'):
                columns = {row[1] for row in cursor.execute('PRAGMA table_info(timesheet)')}
                error_col = f'sync_error_message{suffix}'
                backend_col = f'backend_timesheet_id{suffix}'
                skipped_col = f'sync_skipped_reason{suffix}'
                if error_col in columns:
                    rows = cursor.execute(f"""
                        SELECT id, {error_col} FROM timesheet
                        WHERE {backend_col} IS NULL AND {skipped_col} IS NULL
                        AND {error_col} IS NOT NULL
                    """).fetchall()
                    for row_id, reason in rows:
                        if is_duplicate_error(None, reason):
                            cursor.execute(f"""
                                UPDATE timesheet SET {skipped_col} = ?, {error_col} = NULL
                                WHERE id = ?
                            """, (reason, row_id))

            # Keep delivery history independently of attendance cleanup/re-pulls.
            cursor.execute("""CREATE TABLE IF NOT EXISTS delivery_attempt (
                sync_id TEXT NOT NULL, slot INTEGER NOT NULL CHECK(slot IN (1,2)),
                attempted_at TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 1,
                outcome TEXT NOT NULL, PRIMARY KEY(sync_id, slot))""")
            for slot in (1, 2):
                backend, synced, error = _slot_cols(slot)
                skipped = 'sync_skipped_reason_2' if slot == 2 else 'sync_skipped_reason'
                cursor.execute(f"""INSERT OR IGNORE INTO delivery_attempt
                    (sync_id, slot, attempted_at, outcome)
                    SELECT sync_id, ?, COALESCE({synced}, CURRENT_TIMESTAMP),
                        CASE WHEN {backend} IS NOT NULL OR {skipped} IS NOT NULL
                             THEN 'resolved' ELSE 'unconfirmed' END
                    FROM timesheet WHERE {backend} IS NOT NULL OR {skipped} IS NOT NULL
                        OR {error} IS NOT NULL""", (slot,))

            # Migrate existing device config from api_config to device table
            cursor.execute("SELECT COUNT(*) as count FROM device")
            if cursor.fetchone()['count'] == 0:
                # Check if there's an existing device config in api_config
                cursor.execute("SELECT device_ip, device_port FROM api_config WHERE id = 1")
                row = cursor.fetchone()
                if row and row['device_ip']:
                    # Migrate existing device to new device table
                    cursor.execute("""
                        INSERT INTO device (name, ip, port, enabled)
                        VALUES (?, ?, ?, 1)
                    """, ('Device 1', row['device_ip'], row['device_port'] or 4370))
                    migrated_device_id = cursor.lastrowid
                    # Update existing timesheet records to reference the migrated device
                    cursor.execute("""
                        UPDATE timesheet SET device_id = ? WHERE device_id IS NULL
                    """, (migrated_device_id,))
                    logger.info(f"Migrated existing device config to device table (id={migrated_device_id})")

            conn.commit()
            logger.info("Database initialized successfully")
        except Exception as e:
            conn.rollback()
            logger.error(f"Database initialization error: {e}")
            raise
        finally:
            conn.close()

    # ==================== TIMESHEET METHODS ====================

    def add_timesheet_entry(self, sync_id, employee_id, log_type, date, time, photo_path=None, device_id=None):
        """Add a new timesheet entry"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO timesheet (sync_id, employee_id, log_type, date, time, photo_path, status, device_id)
                VALUES (?, ?, ?, ?, ?, ?, 'success', ?)
            """, (sync_id, employee_id, log_type, date, time, photo_path, device_id))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            return None
        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding timesheet entry: {e}")
            raise
        finally:
            conn.close()

    def get_unsynced_timesheets(self, limit=100, slot=1):
        """Get timesheet entries that still need to be pushed to the given slot's destination"""
        backend_col, _, _ = _slot_cols(slot)
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f"""
                SELECT t.*, e.backend_id as employee_backend_id, e.name as employee_name,
                       e.employee_code as employee_code, d.branch_id as branch_id
                FROM timesheet t
                JOIN employee e ON t.employee_id = e.id
                LEFT JOIN device d ON t.device_id = d.id
                WHERE t.{backend_col} IS NULL
                AND t.{('sync_skipped_reason_2' if int(slot) == 2 else 'sync_skipped_reason')} IS NULL
                AND NOT EXISTS (SELECT 1 FROM delivery_attempt a WHERE a.sync_id=t.sync_id AND a.slot={int(slot)})
                AND t.status = 'success'
                AND COALESCE(t.excluded_from_sync, 0) = 0
                AND t.deleted_at IS NULL
                ORDER BY t.created_at ASC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_unsynced_timesheets_by_ids(self, ids, slot=1, manual_retry=False):
        """Get timesheet entries in the given ID list still unsynced for the given slot"""
        if not ids:
            return []
        backend_col, _, _ = _slot_cols(slot)
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            placeholders = ','.join('?' for _ in ids)
            cursor.execute(f"""
                SELECT t.*, e.backend_id as employee_backend_id, e.name as employee_name,
                       e.employee_code as employee_code, d.branch_id as branch_id
                FROM timesheet t
                JOIN employee e ON t.employee_id = e.id
                LEFT JOIN device d ON t.device_id = d.id
                WHERE t.{backend_col} IS NULL
                AND t.{('sync_skipped_reason_2' if int(slot) == 2 else 'sync_skipped_reason')} IS NULL
                AND {("EXISTS" if manual_retry else "NOT EXISTS")} (
                    SELECT 1 FROM delivery_attempt a WHERE a.sync_id=t.sync_id AND a.slot={int(slot)}
                    {"AND a.outcome != 'resolved'" if manual_retry else ""})
                AND t.status = 'success'
                AND COALESCE(t.excluded_from_sync, 0) = 0
                AND t.deleted_at IS NULL
                AND t.id IN ({placeholders})
                ORDER BY t.created_at ASC
            """, tuple(ids))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def validate_retry_selection(self, payload):
        """Recheck the exact reviewed IDs, destinations and filters before dispatch."""
        items = payload['items']
        if not isinstance(items, list) or not items or len(items) > 10000:
            raise ValueError('Select between 1 and 10,000 destination records')
        for item in items:
            if not isinstance(item, dict) or type(item.get('id')) is not int or item['id'] <= 0 or type(item.get('slot')) is not int or item['slot'] not in (1, 2):
                raise ValueError('Invalid retry selection')
        query, params, state = self._retry_query(payload.get('filters'))
        conn = self.get_connection()
        try:
            conn.execute('CREATE TEMP TABLE selected_retry(id INTEGER, slot INTEGER, PRIMARY KEY(id,slot))')
            conn.executemany('INSERT OR IGNORE INTO selected_retry VALUES(?,?)', [(item['id'], item['slot']) for item in items])
            rows = conn.execute(query + """ SELECT scoped.* FROM scoped JOIN selected_retry s
                ON s.id=scoped.id AND s.slot=scoped.slot WHERE (?='all' OR state=?)""", [*params, state, state]).fetchall()
            eligible = {(r['id'], r['slot']): r for r in rows}
        finally:
            conn.close()
        retry_slots = {}
        for item in items:
            if type(item.get('id')) is not int or type(item.get('slot')) is not int:
                raise ValueError('Invalid retry selection')
            row = eligible.get((item['id'], item['slot']))
            if not row or row['busy']:
                raise ValueError('Some selected records changed or are syncing. Refresh the queue.')
            if row['state'] == 'unconfirmed' and payload.get('reviewed_payroll') is not True:
                raise ValueError('Check unconfirmed records in Payroll before retrying')
            retry_slots.setdefault(item['slot'], set()).add(item['id'])
        return retry_slots

    def claim_delivery(self, ids, slot=1, manual_retry=False):
        """Durably claim before HTTP. A crash leaves an unconfirmed manual item.

        SQLite serializes claims across service instances. Active claims are held
        for 120 seconds, longer than the single HTTP request's 60 second timeout.
        The ledger survives timesheet cleanup and retains the original sync_id.
        """
        if not ids or slot not in (1, 2):
            return []
        backend, _, error = _slot_cols(slot)
        skipped = 'sync_skipped_reason_2' if slot == 2 else 'sync_skipped_reason'
        conn = self.get_connection()
        claimed = []
        try:
            conn.execute('BEGIN IMMEDIATE')
            for row_id in dict.fromkeys(ids):
                row = conn.execute(f"""SELECT sync_id FROM timesheet WHERE id=?
                    AND {backend} IS NULL AND {skipped} IS NULL AND deleted_at IS NULL
                    AND status='success' AND COALESCE(excluded_from_sync,0)=0""", (row_id,)).fetchone()
                if not row:
                    continue
                previous = conn.execute("""SELECT *,
                    (outcome='sending' AND attempted_at > datetime('now', '-120 seconds')) AS busy
                    FROM delivery_attempt WHERE sync_id=? AND slot=?""", (row['sync_id'], slot)).fetchone()
                if previous and (not manual_retry or previous['outcome'] == 'resolved' or previous['busy']):
                    continue
                if manual_retry and not previous:
                    continue
                conn.execute("""INSERT INTO delivery_attempt(sync_id,slot,attempted_at,outcome)
                    VALUES(?,?,datetime('now'),'sending') ON CONFLICT(sync_id,slot) DO UPDATE SET
                    attempted_at=datetime('now'), attempts=attempts+1, outcome='sending'""", (row['sync_id'], slot))
                conn.execute(f"UPDATE timesheet SET {error}=? WHERE id=?",
                    ('Unconfirmed — check Payroll before retrying', row_id))
                claimed.append(row_id)
            conn.commit()
            return claimed
        finally:
            conn.close()

    def _finish_delivery(self, conn, timesheet_id, slot, outcome):
        conn.execute("""UPDATE delivery_attempt SET outcome=? WHERE slot=? AND sync_id=
            (SELECT sync_id FROM timesheet WHERE id=?)""", (outcome, slot, timesheet_id))

    def _retry_query(self, filters=None):
        """Build a parameterized queue query shared by paging and retry validation."""
        filters = {} if filters is None else filters
        if not isinstance(filters, dict):
            raise ValueError('Invalid filters')
        date_from, date_to = filters.get('date_from'), filters.get('date_to')
        for value in (date_from, date_to):
            if value:
                if not isinstance(value, str) or datetime.strptime(value, '%Y-%m-%d').strftime('%Y-%m-%d') != value:
                    raise ValueError('Use YYYY-MM-DD dates')
        if date_from and date_to and date_from > date_to:
            raise ValueError('Start date must be on or before end date')
        employees = filters.get('employee_ids', [])
        if not isinstance(employees, list) or len(employees) > 10000 or any(type(i) is not int or i <= 0 for i in employees):
            raise ValueError('Invalid employees')
        slot_filter = filters.get('slot', 0)
        if type(slot_filter) is not int or slot_filter not in (0, 1, 2):
            raise ValueError('Invalid Payroll destination')
        state = filters.get('state', 'all')
        if state not in ('all', 'failed', 'unconfirmed'):
            raise ValueError('Invalid retry status')
        search = filters.get('search', '')
        if not isinstance(search, str) or len(search) > 100:
            raise ValueError('Search must be at most 100 characters')
        config = self.get_api_config() or {}
        slots = [1, 2] if config.get('push_enabled_2') and config.get('push_username_2') else [1]
        clauses, params = [], []
        for slot in slots:
            backend, _, error = _slot_cols(slot)
            skipped = 'sync_skipped_reason_2' if slot == 2 else 'sync_skipped_reason'
            clauses.append(f"""SELECT t.id, t.employee_id, e.name AS employee_name,
                e.employee_code, t.date, t.time, t.log_type, a.slot, a.attempted_at,
                a.attempts, t.{error} AS reason,
                CASE WHEN a.outcome='failed' THEN 'failed' ELSE 'unconfirmed' END AS state,
                (a.outcome='sending' AND a.attempted_at > datetime('now','-120 seconds')) AS busy
                FROM timesheet t JOIN employee e ON e.id=t.employee_id
                JOIN delivery_attempt a ON a.sync_id=t.sync_id AND a.slot=?
                WHERE t.{backend} IS NULL AND t.{skipped} IS NULL AND a.outcome != 'resolved'
                AND t.deleted_at IS NULL AND t.status='success'
                AND COALESCE(t.excluded_from_sync,0)=0""")
            params.append(slot)
        where = []
        for value, sql in ((date_from, 'date >= ?'), (date_to, 'date <= ?'),
                           (slot_filter, 'slot = ?')):
            if value:
                where.append(sql)
                params.append(value)
        if employees:
            where.append('employee_id IN (' + ','.join('?' for _ in employees) + ')')
            params.extend(employees)
        if search.strip():
            where.append("(instr(lower(employee_name),lower(?)) > 0 OR instr(lower(employee_code),lower(?)) > 0)")
            params.extend([search.strip(), search.strip()])
        scoped = ' AND '.join(where) or '1=1'
        query = f"WITH queue AS ({' UNION ALL '.join(clauses)}), scoped AS (SELECT * FROM queue WHERE {scoped})"
        return query, params, state

    def get_retry_queue(self, filters=None):
        """Full queue for legacy callers; interactive views use bounded SQL pages."""
        query, params, state = self._retry_query(filters)
        conn = self.get_connection()
        try:
            rows = conn.execute(query + " SELECT * FROM scoped WHERE (?='all' OR state=?) ORDER BY date,time,id,slot",
                                [*params, state, state]).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_retry_queue_page(self, filters=None):
        """Aggregate in SQLite and return at most 100 rows, never the whole queue."""
        query, params, state = self._retry_query(filters)
        filters = filters or {}
        page, size, mode = filters.get('page', 1), filters.get('page_size', 25), filters.get('mode', 'employees')
        if type(page) is not int or page < 1 or type(size) is not int or not 1 <= size <= 100:
            raise ValueError('Invalid page; page size must be between 1 and 100')
        if mode not in ('employees', 'logs'):
            raise ValueError('Invalid queue view')
        conn = self.get_connection()
        try:
            # Counts and displayed rows come from the same database snapshot.
            conn.execute('BEGIN')
            counts = {r['state']: r['n'] for r in conn.execute(query +
                ' SELECT state, COUNT(*) AS n FROM scoped GROUP BY state', params)}
            chosen = query + ", chosen AS (SELECT * FROM scoped WHERE (?='all' OR state=?))"
            selected_params = [*params, state, state]
            summary = dict(conn.execute(chosen + """ SELECT COUNT(*) AS uploads,
                COUNT(DISTINCT employee_id) AS employees, COALESCE(SUM(busy=0),0) AS available FROM chosen""", selected_params).fetchone())
            total = summary['employees'] if mode == 'employees' else summary['uploads']
            page = min(page, max(1, (total + size - 1) // size))
            if mode == 'employees':
                sql = """SELECT employee_id, employee_name, employee_code,
                    COUNT(*) AS uploads, COUNT(DISTINCT id) AS logs,
                    MIN(date) AS first_date, MAX(date) AS last_date,
                    COUNT(DISTINCT COALESCE(reason,'')) AS issue_count, MIN(reason) AS reason,
                    SUM(busy=0) AS available
                    FROM chosen GROUP BY employee_id,employee_name,employee_code
                    ORDER BY uploads DESC, employee_name COLLATE NOCASE, employee_id LIMIT ? OFFSET ?"""
            else:
                sql = 'SELECT * FROM chosen ORDER BY date DESC,time DESC,id DESC,slot LIMIT ? OFFSET ?'
            rows = [dict(r) for r in conn.execute(chosen + ' ' + sql, [*selected_params, size, (page-1)*size])]
            return {'rows': rows, 'total': total, 'page': page, 'page_size': size,
                    'counts': {'failed': counts.get('failed', 0), 'unconfirmed': counts.get('unconfirmed', 0)}, **summary}
        finally:
            conn.close()

    def get_retry_selection(self, filters=None):
        """Freeze explicit bulk selection for review; never silently truncate it."""
        query, params, state = self._retry_query(filters)
        conn = self.get_connection()
        try:
            rows = conn.execute(query + """ SELECT * FROM scoped WHERE (?='all' OR state=?)
                AND busy=0 ORDER BY date,time,id,slot LIMIT 10001""", [*params, state, state]).fetchall()
            if len(rows) > 10000:
                raise ValueError('More than 10,000 uploads match. Narrow the dates or employees before retrying.')
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def mark_timesheet_synced(self, timesheet_id, backend_timesheet_id, slot=1):
        """Mark a timesheet entry as successfully synced to the given slot's destination"""
        backend_col, synced_col, error_col = _slot_cols(slot)
        skipped_col = 'sync_skipped_reason_2' if int(slot) == 2 else 'sync_skipped_reason'
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f"""
                UPDATE timesheet
                SET {backend_col} = ?,
                    {synced_col} = ?,
                    {error_col} = NULL,
                    {skipped_col} = NULL
                WHERE id = ?
            """, (backend_timesheet_id, datetime.now(), timesheet_id))
            self._finish_delivery(conn, timesheet_id, slot, 'resolved')
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error marking timesheet as synced: {e}")
            raise
        finally:
            conn.close()

    def mark_timesheet_sync_failed(self, timesheet_id, error_message, slot=1, unconfirmed=False):
        """Mark a timesheet sync as failed for the given slot's destination"""
        _, _, error_col = _slot_cols(slot)
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f"""
                UPDATE timesheet
                SET {error_col} = ?
                WHERE id = ?
            """, (error_message, timesheet_id))
            self._finish_delivery(conn, timesheet_id, slot, 'unconfirmed' if unconfirmed else 'failed')
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error marking sync failed: {e}")
            raise
        finally:
            conn.close()

    def mark_timesheet_duplicate(self, timesheet_id, reason, slot=1):
        """Stop retrying a Payroll-rejected duplicate in just this destination."""
        backend_col, _, error_col = _slot_cols(slot)
        skipped_col = 'sync_skipped_reason_2' if int(slot) == 2 else 'sync_skipped_reason'
        conn = self.get_connection()
        try:
            with conn:
                self._finish_delivery(conn, timesheet_id, slot, 'resolved')
                conn.execute(f"""
                    UPDATE timesheet SET {skipped_col} = ?, {error_col} = NULL
                    WHERE id = ? AND {backend_col} IS NULL
                """, (reason or 'Duplicate record already exists', timesheet_id))
        finally:
            conn.close()

    def baseline_slot_as_synced(self, slot):
        """Mark all currently-unsynced records as already synced for the given slot.

        Used when a second push destination is enabled later, so historical logs
        are not retroactively flooded to it. Sets a sentinel backend id (-1) on
        every not-yet-synced, non-deleted record for that slot. Returns rows updated.
        """
        backend_col, synced_col, error_col = _slot_cols(slot)
        skipped_col = 'sync_skipped_reason_2' if int(slot) == 2 else 'sync_skipped_reason'
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f"""
                UPDATE timesheet
                SET {backend_col} = -1,
                    {synced_col} = ?,
                    {error_col} = NULL
                WHERE {backend_col} IS NULL
                AND {skipped_col} IS NULL
                AND deleted_at IS NULL
            """, (datetime.now(),))
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            conn.rollback()
            logger.error(f"Error baselining slot {slot}: {e}")
            raise
        finally:
            conn.close()

    @staticmethod
    def _new_upload_condition(slot):
        """Match first-attempt eligibility for a timesheet alias t."""
        backend, _, _ = _slot_cols(slot)
        skipped = 'sync_skipped_reason_2' if slot == 2 else 'sync_skipped_reason'
        return f"""t.{backend} IS NULL AND t.{skipped} IS NULL
            AND t.status='success' AND COALESCE(t.excluded_from_sync,0)=0
            AND t.deleted_at IS NULL
            AND NOT EXISTS (SELECT 1 FROM delivery_attempt a
                            WHERE a.sync_id=t.sync_id AND a.slot={slot})"""

    def get_timesheet_stats(self):
        """Count disjoint states across enabled destinations; skipped is not uploaded."""
        config = self.get_api_config() or {}
        slots = [1, 2] if config.get('push_enabled_2') and config.get('push_username_2') else [1]
        synced, resolved, errors = [], [], []
        for slot in slots:
            backend, _, error = _slot_cols(slot)
            skipped = 'sync_skipped_reason_2' if slot == 2 else 'sync_skipped_reason'
            synced.append(f'{backend} IS NOT NULL')
            resolved.append(f'({backend} IS NOT NULL OR {skipped} IS NOT NULL)')
            errors.append(f'({backend} IS NULL AND {skipped} IS NULL AND {error} IS NOT NULL)')
        new_uploads = ' + '.join(f'CASE WHEN {self._new_upload_condition(slot)} THEN 1 ELSE 0 END' for slot in slots)
        synced = ' AND '.join(synced)
        resolved = ' AND '.join(resolved)
        errors = ' OR '.join(errors)
        conn = self.get_connection()
        try:
            row = conn.execute(f"""
                SELECT COUNT(*) AS total,
                    COALESCE(SUM({new_uploads}),0) AS new_uploads,
                    COALESCE(SUM(CASE WHEN {synced} THEN 1 ELSE 0 END), 0) AS synced,
                    COALESCE(SUM(CASE WHEN ({resolved}) AND NOT ({synced}) THEN 1 ELSE 0 END), 0) AS duplicates,
                    COALESCE(SUM(CASE WHEN NOT ({resolved}) AND COALESCE(excluded_from_sync, 0) = 1 THEN 1 ELSE 0 END), 0) AS excluded,
                    COALESCE(SUM(CASE WHEN NOT ({resolved}) AND COALESCE(excluded_from_sync, 0) = 0 AND ({errors}) THEN 1 ELSE 0 END), 0) AS errors,
                    COALESCE(SUM(CASE WHEN NOT ({resolved}) AND COALESCE(excluded_from_sync, 0) = 0 AND NOT ({errors}) THEN 1 ELSE 0 END), 0) AS pending
                FROM timesheet t WHERE deleted_at IS NULL
            """).fetchone()
            return dict(row)
        finally:
            conn.close()

    def soft_delete_timesheets_by_ids(self, ids):
        """Soft-delete specific timesheet records by ID.

        Sets deleted_at on every row in the list that hasn't been soft-deleted
        yet. Returns the number of rows updated.
        """
        if not ids:
            return 0
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            placeholders = ','.join('?' for _ in ids)
            cursor.execute(f"""
                UPDATE timesheet
                SET deleted_at = ?
                WHERE id IN ({placeholders})
                AND deleted_at IS NULL
            """, (datetime.now(), *ids))
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            conn.rollback()
            logger.error(f"Error soft-deleting timesheets by ids: {e}")
            raise
        finally:
            conn.close()

    def set_timesheets_excluded(self, ids, excluded):
        """Mark or unmark a list of timesheet IDs as excluded from sync.

        Exclude pending delivery to either destination, including partially synced rows.
        Returns the number of rows updated.
        """
        if not ids:
            return 0
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            placeholders = ','.join('?' for _ in ids)
            cursor.execute(f"""
                UPDATE timesheet
                SET excluded_from_sync = ?
                WHERE id IN ({placeholders})
                AND (backend_timesheet_id IS NULL OR backend_timesheet_id_2 IS NULL)
                AND deleted_at IS NULL
            """, (1 if excluded else 0, *ids))
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating excluded_from_sync: {e}")
            raise
        finally:
            conn.close()

    def set_timesheets_excluded_by_date_range(self, date_from, date_to, excluded):
        """Mark or unmark all unsynced timesheets within a date range as excluded from sync.

        Rows delivered to both destinations and soft-deleted rows are not modified. Returns the number of rows updated.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE timesheet
                SET excluded_from_sync = ?
                WHERE date >= ? AND date <= ?
                AND (backend_timesheet_id IS NULL OR backend_timesheet_id_2 IS NULL)
                AND deleted_at IS NULL
            """, (1 if excluded else 0, date_from, date_to))
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating excluded_from_sync by date range: {e}")
            raise
        finally:
            conn.close()

    def get_timesheet_by_sync_id(self, sync_id):
        """Get a timesheet entry by sync_id"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM timesheet WHERE sync_id = ?", (sync_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_deleted_timesheets(self, limit=1000, offset=0):
        """Get soft-deleted timesheet entries with pagination"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT t.*, e.name as employee_name, e.employee_code,
                       d.name as device_name
                FROM timesheet t
                JOIN employee e ON t.employee_id = e.id
                LEFT JOIN device d ON t.device_id = d.id
                WHERE t.deleted_at IS NOT NULL
                ORDER BY t.deleted_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_all_timesheets(self, limit=1000, offset=0):
        """Get all timesheet entries with pagination"""
        config = self.get_api_config() or {}
        slots = [1, 2] if config.get('push_enabled_2') and config.get('push_username_2') else [1]
        new_uploads = ' + '.join(f'CASE WHEN {self._new_upload_condition(slot)} THEN 1 ELSE 0 END' for slot in slots)
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f"""
                SELECT t.*, e.name as employee_name, e.employee_code,
                       d.name as device_name, ({new_uploads}) AS new_uploads,
                       (SELECT outcome FROM delivery_attempt a WHERE a.sync_id=t.sync_id AND a.slot=1) AS delivery_outcome_1,
                       (SELECT outcome FROM delivery_attempt a WHERE a.sync_id=t.sync_id AND a.slot=2) AS delivery_outcome_2
                FROM timesheet t
                JOIN employee e ON t.employee_id = e.id
                LEFT JOIN device d ON t.device_id = d.id
                WHERE t.deleted_at IS NULL
                ORDER BY t.date DESC, t.time DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    # ==================== EMPLOYEE METHODS ====================

    def add_or_update_employee(self, backend_id, name, employee_code=None, employee_number=None):
        """Add or update employee record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO employee (backend_id, name, employee_code, employee_number)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(backend_id) DO UPDATE SET
                    name = excluded.name,
                    employee_code = excluded.employee_code,
                    employee_number = excluded.employee_number
            """, (backend_id, name, employee_code, employee_number))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding/updating employee: {e}")
            raise
        finally:
            conn.close()

    def get_employee_by_backend_id(self, backend_id):
        """Get employee by backend ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM employee WHERE backend_id = ?", (backend_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_employee_by_code(self, employee_code):
        """Get employee by employee code (supports alphanumeric codes)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM employee WHERE employee_code = ?", (employee_code,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_all_employees(self):
        """Get all active employees"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM employee WHERE deleted_at IS NULL ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    # ==================== SYNC LOG METHODS ====================

    def create_sync_log(self, sync_type):
        """Create a new sync log entry"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO sync_logs (sync_type, status, started_at)
                VALUES (?, 'started', ?)
            """, (sync_type, datetime.now()))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating sync log: {e}")
            raise
        finally:
            conn.close()

    def update_sync_log(self, log_id, status, records_processed=0, records_success=0,
                       records_failed=0, error_message=None, metadata=None):
        """Update sync log with results"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            cursor.execute("""
                UPDATE sync_logs
                SET status = ?,
                    records_processed = ?,
                    records_success = ?,
                    records_failed = ?,
                    error_message = ?,
                    completed_at = ?,
                    metadata = ?
                WHERE id = ?
            """, (status, records_processed, records_success, records_failed,
                  error_message, datetime.now(), metadata_json, log_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating sync log: {e}")
            raise
        finally:
            conn.close()

    def get_recent_sync_logs(self, sync_type=None, limit=50):
        """Get recent sync logs"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if sync_type:
                cursor.execute("""
                    SELECT * FROM sync_logs
                    WHERE sync_type = ?
                    ORDER BY started_at DESC
                    LIMIT ?
                """, (sync_type, limit))
            else:
                cursor.execute("""
                    SELECT * FROM sync_logs
                    ORDER BY started_at DESC
                    LIMIT ?
                """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def log_config_change(self, message="Configuration updated"):
        """Log a configuration change event"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            now = datetime.now()
            cursor.execute("""
                INSERT INTO sync_logs (sync_type, status, started_at, completed_at, error_message)
                VALUES ('config', 'success', ?, ?, ?)
            """, (now, now, message))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            conn.rollback()
            logger.error(f"Error logging config change: {e}")
            raise
        finally:
            conn.close()

    def log_other_event(self, message, status="success"):
        """Log other system events (cleanup, maintenance, etc.)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            now = datetime.now()
            cursor.execute("""
                INSERT INTO sync_logs (sync_type, status, started_at, completed_at, error_message)
                VALUES ('other', ?, ?, ?, ?)
            """, (status, now, now, message))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            conn.rollback()
            logger.error(f"Error logging other event: {e}")
            raise
        finally:
            conn.close()

    # ==================== API CONFIG METHODS ====================

    def get_api_config(self):
        """Get API configuration"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM api_config WHERE id = 1")
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_api_config(self, **kwargs):
        """Update API configuration"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Build dynamic update query
            set_clauses = [f"{key} = ?" for key in kwargs.keys()]
            values = list(kwargs.values())
            values.append(datetime.now())  # for updated_at
            values.append(1)  # for WHERE id = 1

            query = f"""
                UPDATE api_config
                SET {', '.join(set_clauses)}, updated_at = ?
                WHERE id = ?
            """
            cursor.execute(query, values)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating API config: {e}")
            raise
        finally:
            conn.close()

    def update_last_sync_time(self, sync_type):
        """Update last pull/push time"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            field = f"last_{sync_type}_at"
            cursor.execute(f"""
                UPDATE api_config
                SET {field} = ?, updated_at = ?
                WHERE id = 1
            """, (datetime.now(), datetime.now()))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating last sync time: {e}")
            raise
        finally:
            conn.close()

    def get_device_ip(self):
        """Get configured device IP"""
        config = self.get_api_config()
        return config.get('device_ip') if config else None

    def get_device_port(self):
        """Get configured device port"""
        config = self.get_api_config()
        return config.get('device_port', 4370) if config else 4370

    def update_push_token(self, token, user_logged=None, slot=1):
        """Update YAHSHUA push token and user info for the given slot"""
        token_col, created_col, user_col = _token_cols(slot)
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if token is None:
                # Logout - clear token and user info
                cursor.execute(f"""
                    UPDATE api_config
                    SET {token_col} = NULL, {created_col} = NULL,
                        {user_col} = NULL, updated_at = ?
                    WHERE id = 1
                """, (datetime.now(),))
            else:
                # Login - store token and user info
                cursor.execute(f"""
                    UPDATE api_config
                    SET {token_col} = ?, {created_col} = ?,
                        {user_col} = ?, updated_at = ?
                    WHERE id = 1
                """, (token, datetime.now(), user_logged, datetime.now()))
            conn.commit()
            logger.info(f"Push token (slot {slot}) updated successfully")
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating push token: {e}")
            raise
        finally:
            conn.close()

    def get_push_token(self, slot=1):
        """Get current YAHSHUA push token for the given slot"""
        token_col, _, _ = _token_cols(slot)
        config = self.get_api_config()
        return config.get(token_col) if config else None

    # ==================== DEVICE METHODS ====================

    def get_devices(self):
        """Get all active (non-deleted) devices"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT * FROM device
                WHERE deleted_at IS NULL
                ORDER BY created_at ASC
            """)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_enabled_devices(self):
        """Get all enabled (and non-deleted) devices"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT * FROM device
                WHERE enabled = 1 AND deleted_at IS NULL
                ORDER BY created_at ASC
            """)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_device(self, device_id):
        """Get a single device by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM device WHERE id = ?", (device_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def add_device(self, name, ip, port=4370, comm_key=0, branch_id=None):
        """Add a new device"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO device (name, ip, port, comm_key, branch_id, enabled)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (name, ip, port, comm_key or 0, branch_id or None))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            conn.rollback()
            if 'UNIQUE constraint failed' in str(e) or 'idx_device_unique_ip_active' in str(e):
                raise Exception(f"A device with IP '{ip}' already exists")
            raise
        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding device: {e}")
            raise
        finally:
            conn.close()

    def update_device(self, device_id, name=None, ip=None, port=None, comm_key=None, branch_id=None, enabled=None):
        """Update device configuration"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            updates = []
            values = []
            if name is not None:
                updates.append("name = ?")
                values.append(name)
            if ip is not None:
                updates.append("ip = ?")
                values.append(ip)
            if port is not None:
                updates.append("port = ?")
                values.append(port)
            if comm_key is not None:
                updates.append("comm_key = ?")
                values.append(comm_key)
            if branch_id is not None:
                updates.append("branch_id = ?")
                values.append(branch_id if branch_id else None)
            if enabled is not None:
                updates.append("enabled = ?")
                values.append(1 if enabled else 0)

            if not updates:
                return False

            updates.append("updated_at = ?")
            values.append(datetime.now())
            values.append(device_id)

            query = f"UPDATE device SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.IntegrityError as e:
            conn.rollback()
            if 'UNIQUE constraint failed' in str(e) or 'idx_device_unique_ip_active' in str(e):
                raise Exception(f"A device with IP '{ip}' already exists")
            raise
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating device: {e}")
            raise
        finally:
            conn.close()

    def delete_device(self, device_id):
        """Soft delete a device (sets deleted_at timestamp)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE device
                SET deleted_at = ?, updated_at = ?
                WHERE id = ? AND deleted_at IS NULL
            """, (datetime.now(), datetime.now(), device_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            logger.error(f"Error deleting device: {e}")
            raise
        finally:
            conn.close()

    def update_device_last_pull(self, device_id):
        """Update last pull timestamp for a device"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE device
                SET last_pull_at = ?, updated_at = ?
                WHERE id = ?
            """, (datetime.now(), datetime.now(), device_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating device last pull: {e}")
            raise
        finally:
            conn.close()
