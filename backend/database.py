"""
ZKTeco Integration Tool - Database Manager
SQLite database for storing timesheet data and sync status
"""

import sqlite3
import json
import sys
import os
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Determine if running as frozen executable
IS_FROZEN = getattr(sys, 'frozen', False)

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

            # Create indexes for deleted_at (after column exists)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_device_deleted_at ON device(deleted_at)")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_device_unique_ip_active ON device(ip) WHERE deleted_at IS NULL")

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
            logger.warning(f"Duplicate timesheet entry: {sync_id}")
            return None
        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding timesheet entry: {e}")
            raise
        finally:
            conn.close()

    def get_unsynced_timesheets(self, limit=100):
        """Get timesheet entries that need to be pushed to backend"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT t.*, e.backend_id as employee_backend_id, e.name as employee_name,
                       e.employee_code as employee_code
                FROM timesheet t
                JOIN employee e ON t.employee_id = e.id
                WHERE t.backend_timesheet_id IS NULL
                AND t.status = 'success'
                ORDER BY t.created_at ASC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def mark_timesheet_synced(self, timesheet_id, backend_timesheet_id):
        """Mark a timesheet entry as successfully synced"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE timesheet
                SET backend_timesheet_id = ?,
                    synced_at = ?,
                    sync_error_message = NULL
                WHERE id = ?
            """, (backend_timesheet_id, datetime.now(), timesheet_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error marking timesheet as synced: {e}")
            raise
        finally:
            conn.close()

    def mark_timesheet_sync_failed(self, timesheet_id, error_message):
        """Mark a timesheet sync as failed"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE timesheet
                SET sync_error_message = ?
                WHERE id = ?
            """, (error_message, timesheet_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error marking sync failed: {e}")
            raise
        finally:
            conn.close()

    def get_timesheet_stats(self):
        """Get statistics about timesheet entries"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN backend_timesheet_id IS NOT NULL THEN 1 ELSE 0 END) as synced,
                    SUM(CASE WHEN backend_timesheet_id IS NULL THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN sync_error_message IS NOT NULL THEN 1 ELSE 0 END) as errors
                FROM timesheet
            """)
            return dict(cursor.fetchone())
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

    def get_all_timesheets(self, limit=1000, offset=0):
        """Get all timesheet entries with pagination"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT t.*, e.name as employee_name, e.employee_code,
                       d.name as device_name
                FROM timesheet t
                JOIN employee e ON t.employee_id = e.id
                LEFT JOIN device d ON t.device_id = d.id
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

    def update_push_token(self, token, user_logged=None):
        """Update YAHSHUA push token and user info"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if token is None:
                # Logout - clear token and user info
                cursor.execute("""
                    UPDATE api_config
                    SET push_token = NULL, push_token_created_at = NULL,
                        push_user_logged = NULL, updated_at = ?
                    WHERE id = 1
                """, (datetime.now(),))
            else:
                # Login - store token and user info
                cursor.execute("""
                    UPDATE api_config
                    SET push_token = ?, push_token_created_at = ?,
                        push_user_logged = ?, updated_at = ?
                    WHERE id = 1
                """, (token, datetime.now(), user_logged, datetime.now()))
            conn.commit()
            logger.info("Push token updated successfully")
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating push token: {e}")
            raise
        finally:
            conn.close()

    def get_push_token(self):
        """Get current YAHSHUA push token"""
        config = self.get_api_config()
        return config.get('push_token') if config else None

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

    def add_device(self, name, ip, port=4370):
        """Add a new device"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO device (name, ip, port, enabled)
                VALUES (?, ?, ?, 1)
            """, (name, ip, port))
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

    def update_device(self, device_id, name=None, ip=None, port=None, enabled=None):
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
