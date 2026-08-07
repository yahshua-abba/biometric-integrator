"""
Biometric Integration - Python-JavaScript Bridge
Provides QWebChannel bridge for communication between PyQt6 and Vue.js
"""

from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal, QThread, QMetaObject, Qt, Q_ARG
import json
import logging
import os
import sys
import tempfile
from datetime import datetime
import threading
from version import APP_VERSION

logger = logging.getLogger(__name__)

# Determine LOG_DIR (same logic as main.py to avoid circular import)
IS_FROZEN = getattr(sys, 'frozen', False)
if IS_FROZEN:
    LOG_DIR = os.path.join(tempfile.gettempdir(), 'zkteco_integration', 'system_logs')
else:
    LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'system_logs')

class Bridge(QObject):
    """Bridge class for Python-JavaScript communication via QWebChannel"""

    # Signals for sending data to JavaScript
    syncStatusUpdated = pyqtSignal(str)  # Emits JSON string with sync status
    syncProgressUpdated = pyqtSignal(str)  # Emits JSON string with progress
    syncCompleted = pyqtSignal(str)  # Emits JSON string with results
    updateDownloadProgress = pyqtSignal(str)  # Emits JSON string with download progress

    def __init__(self, database, pull_service, push_service, scheduler=None, push_service_2=None):
        super().__init__()
        self.database = database
        self.pull_service = pull_service
        self.push_service = push_service
        self.push_service_2 = push_service_2
        self.scheduler = scheduler
        logger.info("Bridge initialized")

    def set_scheduler(self, scheduler):
        """Set the scheduler reference (called after scheduler is created)"""
        self.scheduler = scheduler

    def _push_service_for_slot(self, slot):
        """Return the PushService bound to the given slot (falls back to primary)."""
        if int(slot) == 2 and self.push_service_2 is not None:
            return self.push_service_2
        return self.push_service

    def _active_push_services(self):
        """Return the push services that should run: primary always, secondary
        only when it is enabled in config and has credentials configured."""
        services = [self.push_service]
        config = self.database.get_api_config() or {}
        if (self.push_service_2 is not None
                and config.get('push_enabled_2')
                and self.push_service_2.is_configured()):
            services.append(self.push_service_2)
        return services

    # ==================== TIMESHEET METHODS ====================

    @pyqtSlot(result=str)
    def getTimesheetStats(self):
        """Get timesheet statistics"""
        try:
            stats = self.database.get_timesheet_stats()
            return json.dumps({"success": True, "data": stats})
        except Exception as e:
            logger.error(f"Error getting timesheet stats: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @pyqtSlot(int, int, result=str)
    def getAllTimesheets(self, limit=1000, offset=0):
        """Get all timesheets with pagination"""
        try:
            timesheets = self.database.get_all_timesheets(limit, offset)
            return json.dumps({"success": True, "data": timesheets})
        except Exception as e:
            logger.error(f"Error getting timesheets: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @pyqtSlot(int, int, result=str)
    def getDeletedTimesheets(self, limit=1000, offset=0):
        """Get soft-deleted (cleared) timesheets with pagination"""
        try:
            timesheets = self.database.get_deleted_timesheets(limit, offset)
            return json.dumps({"success": True, "data": timesheets})
        except Exception as e:
            logger.error(f"Error getting deleted timesheets: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @pyqtSlot(int, result=str)
    def getUnsyncedTimesheets(self, limit=100):
        """Get unsynced timesheets"""
        try:
            timesheets = self.database.get_unsynced_timesheets(limit)
            return json.dumps({"success": True, "data": timesheets})
        except Exception as e:
            logger.error(f"Error getting unsynced timesheets: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @pyqtSlot(int, result=str)
    def retryFailedTimesheet(self, timesheet_id):
        """Retry syncing a failed timesheet.

        Clears the error message for both destinations so the record re-enters the
        push queue of whichever destination(s) it has not yet synced to.
        """
        try:
            conn = self.database.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE timesheet
                SET sync_error_message = NULL,
                    sync_error_message_2 = NULL
                WHERE id = ?
            """, (timesheet_id,))
            conn.commit()
            conn.close()
            return json.dumps({"success": True})
        except Exception as e:
            logger.error(f"Error retrying timesheet: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @pyqtSlot(str, str, bool, result=str)
    def clearTimesheets(self, date_from, date_to, only_synced=True):
        """Clear timesheet records within a date range.

        All deleted records are soft-deleted (deleted_at set) regardless of
        whether they were synced. This preserves the sync_id in the database so
        the biometric device cannot re-supply the same log on a future pull —
        the UNIQUE constraint on sync_id blocks re-insertion and the record
        never re-enters the push queue.
        """
        try:
            conn = self.database.get_connection()
            cursor = conn.cursor()
            now = datetime.now()

            if only_synced:
                # Soft-delete only synced records
                cursor.execute("""
                    UPDATE timesheet
                    SET deleted_at = ?
                    WHERE date >= ? AND date <= ?
                    AND backend_timesheet_id IS NOT NULL
                    AND deleted_at IS NULL
                """, (now, date_from, date_to))
            else:
                # Soft-delete all records (synced and unsynced).
                # Unsynced records are also soft-deleted so that a re-pull from
                # the device does not bring them back — once deleted, they stay gone.
                cursor.execute("""
                    UPDATE timesheet
                    SET deleted_at = ?
                    WHERE date >= ? AND date <= ?
                    AND deleted_at IS NULL
                """, (now, date_from, date_to))

            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()

            filter_text = "synced " if only_synced else ""
            logger.info(f"Cleared {deleted_count} {filter_text}timesheet records from {date_from} to {date_to}")
            return json.dumps({
                "success": True,
                "message": f"Deleted {deleted_count} {filter_text}timesheet records",
                "deleted_count": deleted_count
            })
        except Exception as e:
            logger.error(f"Error clearing timesheets: {e}")
            return json.dumps({"success": False, "error": str(e)})

    # ==================== EMPLOYEE METHODS ====================

    @pyqtSlot(result=str)
    def getAllEmployees(self):
        """Get all active employees"""
        try:
            employees = self.database.get_all_employees()
            return json.dumps({"success": True, "data": employees})
        except Exception as e:
            logger.error(f"Error getting employees: {e}")
            return json.dumps({"success": False, "error": str(e)})

    # ==================== SYNC METHODS ====================

    @pyqtSlot(str, str, result=str)
    def startPullSync(self, date_from, date_to):
        """Manually trigger pull sync from all enabled ZKTeco devices (runs in background thread)"""
        return self.startPullSyncWithDevice(date_from, date_to, -1)  # -1 means all devices

    @pyqtSlot(str, str, int, result=str)
    def startPullSyncWithDevice(self, date_from, date_to, device_id):
        """Manually trigger pull sync from ZKTeco device(s) with date range (runs in background thread)

        Args:
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            device_id: Device ID to sync, or -1 for all enabled devices
        """
        # Check if any devices are configured
        devices = self.database.get_enabled_devices()
        if not devices:
            # Fallback: check legacy api_config for backwards compatibility
            config = self.database.get_api_config()
            if not config or not config.get('device_ip'):
                return json.dumps({
                    "success": False,
                    "error": "No devices configured. Go to Configuration and add a device."
                })

        # Convert -1 to None (meaning all devices)
        target_device_id = None if device_id == -1 else device_id

        if target_device_id is not None:
            device = self.database.get_device(target_device_id)
            if not device:
                return json.dumps({"success": False, "error": "Device not found"})
            logger.info(f"Manual pull sync triggered for device '{device['name']}': {date_from} to {date_to}")
        else:
            logger.info(f"Manual pull sync triggered for all devices: {date_from} to {date_to}")

        # Start pull in background thread
        def run_pull():
            try:
                # Progress callback to emit updates to frontend
                def on_progress(progress_dict):
                    logger.info(f"Pull progress: {progress_dict}")
                    self.syncProgressUpdated.emit(json.dumps(progress_dict))

                success, message, stats = self.pull_service.pull_data(
                    date_from, date_to, device_id=target_device_id, progress_callback=on_progress
                )

                result = {
                    "success": success,
                    "message": message,
                    "stats": stats
                }

                # Emit signal to update UI
                self.syncCompleted.emit(json.dumps({
                    "type": "pull",
                    "result": result
                }))

            except Exception as e:
                logger.error(f"Error in pull sync thread: {e}")
                self.syncCompleted.emit(json.dumps({
                    "type": "pull",
                    "result": {"success": False, "error": str(e)}
                }))

        thread = threading.Thread(target=run_pull, daemon=True)
        thread.start()

        # Return immediately - results will come via signals
        return json.dumps({"success": True, "message": "Pull sync started"})

    @pyqtSlot(result=str)
    def startPushSync(self):
        """Manually trigger push sync to cloud payroll (runs in background thread)"""
        return self._start_push_sync(timesheet_ids=None)

    @pyqtSlot(str, result=str)
    def deleteTimesheetsByIds(self, ids_json):
        """Soft-delete specific timesheet records by ID.

        Args:
            ids_json: JSON-encoded list of timesheet IDs to delete.
        """
        try:
            ids = json.loads(ids_json) if ids_json else []
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid timesheet ids payload: {e}")
            return json.dumps({"success": False, "error": "Invalid timesheet ids"})

        ids = [int(i) for i in ids if i is not None]
        if not ids:
            return json.dumps({"success": False, "error": "No timesheet IDs provided"})

        try:
            deleted = self.database.soft_delete_timesheets_by_ids(ids)
            return json.dumps({
                "success": True,
                "deleted": deleted,
                "message": f"{deleted} record(s) deleted"
            })
        except Exception as e:
            logger.error(f"Error deleting timesheets by ids: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @pyqtSlot(str, str, bool, result=str)
    def setTimesheetExcludedByDateRange(self, date_from, date_to, excluded):
        """Mark or unmark all unsynced timesheets within a date range as excluded from sync.

        Args:
            date_from: Start date string (YYYY-MM-DD).
            date_to:   End date string (YYYY-MM-DD).
            excluded:  True to mark as do-not-sync, False to unmark.
        """
        try:
            updated = self.database.set_timesheets_excluded_by_date_range(date_from, date_to, bool(excluded))
            verb = "marked as do-not-sync" if excluded else "unmarked"
            return json.dumps({
                "success": True,
                "updated": updated,
                "message": f"{updated} record(s) {verb}"
            })
        except Exception as e:
            logger.error(f"Error updating exclusion flag by date range: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @pyqtSlot(str, bool, result=str)
    def setTimesheetExcluded(self, ids_json, excluded):
        """Mark or unmark a list of timesheet IDs as excluded from sync.

        Args:
            ids_json: JSON-encoded list of timesheet IDs.
            excluded: True to mark as do-not-sync, False to unmark.
        """
        try:
            ids = json.loads(ids_json) if ids_json else []
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid timesheet ids payload: {e}")
            return json.dumps({"success": False, "error": "Invalid timesheet ids"})

        ids = [int(i) for i in ids if i is not None]
        if not ids:
            return json.dumps({"success": False, "error": "No timesheet IDs provided"})

        try:
            updated = self.database.set_timesheets_excluded(ids, bool(excluded))
            verb = "excluded" if excluded else "included"
            return json.dumps({
                "success": True,
                "updated": updated,
                "message": f"{updated} record(s) {verb}"
            })
        except Exception as e:
            logger.error(f"Error updating exclusion flag: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @pyqtSlot(str, result=str)
    def startPushSyncForIds(self, ids_json):
        """Manually trigger push sync for a specific set of timesheet IDs.

        Args:
            ids_json: JSON-encoded list of timesheet IDs to push.
        """
        try:
            ids = json.loads(ids_json) if ids_json else []
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid timesheet ids payload: {e}")
            return json.dumps({"success": False, "error": "Invalid timesheet ids"})

        ids = [int(i) for i in ids if i is not None]
        if not ids:
            return json.dumps({"success": False, "error": "No timesheet IDs provided"})

        return self._start_push_sync(timesheet_ids=ids)

    def _start_push_sync(self, timesheet_ids=None):
        """Shared implementation: push to every active destination simultaneously.

        Each enabled push slot runs in its own thread with its own token/session
        and its own per-record status columns, so the same logs are delivered to
        both payroll systems at once. A single combined result is emitted once all
        destinations finish.
        """
        scope = f"{len(timesheet_ids)} selected records" if timesheet_ids else "all unsynced"
        services = self._active_push_services()
        logger.info(f"Manual push sync triggered from UI: {scope} -> {[s.label for s in services]}")

        def run_all():
            results = {}
            lock = threading.Lock()

            def run_one(svc):
                try:
                    def on_progress(progress_dict):
                        payload = dict(progress_dict)
                        payload['slot'] = svc.slot
                        payload['config_label'] = svc.label
                        payload['config_total'] = len(services)
                        self.syncProgressUpdated.emit(json.dumps(payload))

                    success, message, stats = svc.push_data(
                        progress_callback=on_progress,
                        timesheet_ids=timesheet_ids
                    )
                    with lock:
                        results[svc.slot] = {
                            "slot": svc.slot, "label": svc.label,
                            "success": success, "message": message, "stats": stats
                        }
                except Exception as e:
                    logger.error(f"Error in push sync thread ({svc.label}): {e}")
                    with lock:
                        results[svc.slot] = {
                            "slot": svc.slot, "label": svc.label,
                            "success": False, "error": str(e), "stats": {}
                        }

            threads = []
            for svc in services:
                t = threading.Thread(target=run_one, args=(svc,), daemon=True)
                t.start()
                threads.append(t)
            for t in threads:
                t.join()

            # Aggregate results across all destinations
            overall_success = all(r.get("success") for r in results.values())
            agg = {"processed": 0, "success": 0, "failed": 0, "skipped": 0}
            parts = []
            for slot in sorted(results):
                r = results[slot]
                for key in agg:
                    agg[key] += (r.get("stats") or {}).get(key, 0)
                detail = r.get("error") or r.get("message") or ""
                parts.append(f"{r['label']}: {detail}")

            combined_message = "  |  ".join(parts) if parts else "No push destinations configured"

            self.syncCompleted.emit(json.dumps({
                "type": "push",
                "result": {
                    "success": overall_success,
                    "message": combined_message,
                    "stats": agg,
                    "per_config": list(results.values())
                }
            }))

        thread = threading.Thread(target=run_all, daemon=True)
        thread.start()

        # Return immediately - results will come via signals
        return json.dumps({"success": True, "message": "Push sync started"})

    @pyqtSlot(result=str)
    def getSyncLogs(self):
        """Get recent sync logs"""
        try:
            logs = self.database.get_recent_sync_logs(limit=100)
            return json.dumps({"success": True, "data": logs})
        except Exception as e:
            logger.error(f"Error getting sync logs: {e}")
            return json.dumps({"success": False, "error": str(e)})

    # ==================== CONFIG METHODS ====================

    @pyqtSlot(result=str)
    def getApiConfig(self):
        """Get API configuration"""
        try:
            config = self.database.get_api_config()
            # Don't send credentials to frontend for security
            if config:
                config['push_credentials'] = '***' if config.get('push_credentials') else None
                config['push_password'] = '***' if config.get('push_password') else None
                # Device config - check if configured
                config['device_configured'] = bool(config.get('device_ip'))
                # Push login state - include token existence and user info (Config 1)
                config['push_token_exists'] = bool(config.get('push_token'))
                config['push_token'] = '***' if config.get('push_token') else None

                # Second push destination (Config 2)
                config['push_password_2'] = '***' if config.get('push_password_2') else None
                config['push_token_2_exists'] = bool(config.get('push_token_2'))
                config['push_token_2'] = '***' if config.get('push_token_2') else None
                config['push_enabled_2'] = bool(config.get('push_enabled_2'))

                # Format datetimes for display
                for field in ('push_token_created_at', 'push_token_created_at_2'):
                    if config.get(field):
                        try:
                            dt = datetime.fromisoformat(str(config[field]))
                            config[field] = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            pass
            return json.dumps({"success": True, "data": config})
        except Exception as e:
            logger.error(f"Error getting API config: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @pyqtSlot(str, result=str)
    def updateApiConfig(self, config_json):
        """Update API configuration"""
        try:
            config = json.loads(config_json)

            # Only update provided fields. Note: push_enabled_2 is intentionally NOT
            # here — it is toggled via setPushConfig2Enabled so the history-baseline
            # decision can be handled explicitly.
            update_fields = {}
            allowed_fields = [
                'device_ip', 'device_port',
                'push_url', 'push_auth_type', 'push_credentials',
                'push_username', 'push_password',
                'push_url_2', 'push_username_2', 'push_password_2',
                'pull_interval_minutes', 'push_interval_minutes'
            ]

            for field in allowed_fields:
                if field in config:
                    # Skip if credentials/passwords are masked or empty (don't overwrite existing)
                    if 'credentials' in field or 'password' in field:
                        if config[field] == '***' or config[field] == '' or config[field] is None:
                            continue
                    update_fields[field] = config[field]

            self.database.update_api_config(**update_fields)
            logger.info(f"API config updated: {list(update_fields.keys())}")

            # Log config change (only if fields were actually updated)
            if update_fields:
                self.database.log_config_change("Configuration saved")

            return json.dumps({"success": True, "message": "Configuration updated successfully"})
        except Exception as e:
            logger.error(f"Error updating API config: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @pyqtSlot(str, result=str)
    def testConnection(self, connection_type):
        """Test connection (device, push/push1, or push2)"""
        try:
            if connection_type == 'device':
                success, message = self.pull_service.test_connection()
            elif connection_type in ('push', 'push1'):
                success, message = self.push_service.test_connection()
            elif connection_type == 'push2':
                success, message = self._push_service_for_slot(2).test_connection()
            else:
                return json.dumps({"success": False, "error": "Invalid connection type"})

            if success:
                return json.dumps({"success": True, "message": message})
            else:
                return json.dumps({"success": False, "error": message})
        except Exception as e:
            logger.error(f"Error testing connection: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @pyqtSlot(result=str)
    def getDeviceUsers(self):
        """Get list of users from ZKTeco device"""
        try:
            users = self.pull_service.get_device_users()
            return json.dumps({"success": True, "data": users})
        except Exception as e:
            logger.error(f"Error getting device users: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @pyqtSlot(str, str, int, result=str)
    def loginPush(self, username, password, slot=1):
        """Login to a YAHSHUA Payroll destination and store its token.

        Args:
            username: Payroll username/email.
            password: Payroll password.
            slot: Push destination (1 = primary, 2 = secondary).
        """
        try:
            slot = int(slot) if slot else 1
            logger.info(f"Attempting YAHSHUA login (slot {slot}) for {username}")

            # Save credentials first to the slot's columns
            suffix = '_2' if slot == 2 else ''
            self.database.update_api_config(**{
                f'push_username{suffix}': username,
                f'push_password{suffix}': password,
            })

            # Authenticate using the slot's service
            service = self._push_service_for_slot(slot)
            auth_result = service.authenticate(username, password)

            # Log the login
            self.database.log_config_change(f"YAHSHUA login successful (destination {slot})")

            return json.dumps({
                "success": True,
                "message": f"Logged in as {auth_result['user_logged']}",
                "user_logged": auth_result['user_logged'],
                "company_name": auth_result['company_name']
            })
        except Exception as e:
            logger.error(f"Error logging in to YAHSHUA: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @pyqtSlot(int, result=str)
    def logoutPush(self, slot=1):
        """Logout from a YAHSHUA Payroll destination (clear its token)"""
        try:
            slot = int(slot) if slot else 1
            logger.info(f"Logging out from YAHSHUA (slot {slot})")
            self.database.update_push_token(None, slot=slot)

            # Log the logout
            self.database.log_config_change(f"YAHSHUA logout (destination {slot})")

            return json.dumps({"success": True, "message": "Logged out successfully"})
        except Exception as e:
            logger.error(f"Error logging out from YAHSHUA: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @pyqtSlot(bool, bool, result=str)
    def setPushConfig2Enabled(self, enabled, push_history=False):
        """Enable or disable the second push destination.

        When enabling, by default existing (historical) records are baselined as
        already-synced to Config 2 so they are not retroactively flooded to the new
        destination. Pass push_history=True to instead push the full backlog.

        Args:
            enabled: True to enable the second destination, False to disable.
            push_history: When enabling, True to also push existing records.
        """
        try:
            baselined = 0
            if enabled and not push_history:
                baselined = self.database.baseline_slot_as_synced(2)

            self.database.update_api_config(push_enabled_2=1 if enabled else 0)
            self.database.log_config_change(
                f"Second push destination {'enabled' if enabled else 'disabled'}"
            )
            return json.dumps({
                "success": True,
                "enabled": bool(enabled),
                "baselined": baselined,
                "message": (
                    f"Second destination enabled ({baselined} existing records skipped)"
                    if enabled and not push_history else
                    "Second destination enabled (existing records will be pushed)"
                    if enabled else
                    "Second destination disabled"
                )
            })
        except Exception as e:
            logger.error(f"Error toggling second push destination: {e}")
            return json.dumps({"success": False, "error": str(e)})

    # ==================== DEVICE MANAGEMENT METHODS ====================

    @pyqtSlot(result=str)
    def getDevices(self):
        """Get all configured devices"""
        try:
            devices = self.database.get_devices()
            return json.dumps({"success": True, "data": devices})
        except Exception as e:
            logger.error(f"Error getting devices: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @pyqtSlot(str, str, int, int, str, result=str)
    def addDevice(self, name, ip, port, comm_key, branch_id):
        """Add a new ZKTeco device"""
        try:
            if not name or not ip:
                return json.dumps({"success": False, "error": "Name and IP are required"})

            device_id = self.database.add_device(name, ip, port or 4370, comm_key or 0, branch_id or None)
            logger.info(f"Added new device: {name} ({ip}:{port}) branch_id={branch_id}")

            # Log the config change
            self.database.log_config_change(f"Added device: {name}")

            return json.dumps({
                "success": True,
                "message": f"Device '{name}' added successfully",
                "device_id": device_id
            })
        except Exception as e:
            logger.error(f"Error adding device: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @pyqtSlot(int, str, str, int, int, str, bool, result=str)
    def updateDevice(self, device_id, name, ip, port, comm_key, branch_id, enabled):
        """Update an existing device"""
        try:
            success = self.database.update_device(
                device_id,
                name=name if name else None,
                ip=ip if ip else None,
                port=port if port else None,
                comm_key=comm_key,
                branch_id=branch_id,
                enabled=enabled
            )

            if success:
                logger.info(f"Updated device {device_id}: {name}")
                self.database.log_config_change(f"Updated device: {name}")
                return json.dumps({"success": True, "message": "Device updated successfully"})
            else:
                return json.dumps({"success": False, "error": "Device not found"})
        except Exception as e:
            logger.error(f"Error updating device: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @pyqtSlot(int, result=str)
    def deleteDevice(self, device_id):
        """Delete a device"""
        try:
            # Get device name before deleting for logging
            device = self.database.get_device(device_id)
            device_name = device['name'] if device else f"Device {device_id}"

            success = self.database.delete_device(device_id)

            if success:
                logger.info(f"Deleted device: {device_name}")
                self.database.log_config_change(f"Deleted device: {device_name}")
                return json.dumps({"success": True, "message": "Device deleted successfully"})
            else:
                return json.dumps({"success": False, "error": "Device not found"})
        except Exception as e:
            logger.error(f"Error deleting device: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @pyqtSlot(int, result=str)
    def testDeviceConnection(self, device_id):
        """Test connection to a specific device"""
        try:
            device = self.database.get_device(device_id)
            if not device:
                return json.dumps({"success": False, "error": "Device not found"})

            success, message = self.pull_service.test_connection(device_id)

            if success:
                return json.dumps({"success": True, "message": message})
            else:
                return json.dumps({"success": False, "error": message})
        except Exception as e:
            logger.error(f"Error testing device connection: {e}")
            return json.dumps({"success": False, "error": str(e)})

    # ==================== UTILITY METHODS ====================

    @pyqtSlot(result=str)
    def getAppInfo(self):
        """Get application information"""
        return json.dumps({
            "success": True,
            "data": {
                "name": "Biometric Integration",
                "version": APP_VERSION,
                "description": "Sync attendance data from ZKTeco devices to cloud payroll"
            }
        })

    @pyqtSlot(str)
    def logMessage(self, message):
        """Log message from JavaScript"""
        logger.info(f"[JS] {message}")

    @pyqtSlot(result=str)
    def triggerCleanup(self):
        """Manually trigger the cleanup of old records"""
        try:
            if self.scheduler:
                self.scheduler.trigger_cleanup_now()
                return json.dumps({"success": True, "message": "Cleanup triggered"})
            else:
                return json.dumps({"success": False, "error": "Scheduler not initialized"})
        except Exception as e:
            logger.error(f"Error triggering cleanup: {e}")
            return json.dumps({"success": False, "error": str(e)})

    # ==================== UPDATE METHODS ====================

    @pyqtSlot(result=str)
    def checkForUpdates(self):
        """Check GitHub Releases for a newer version"""
        try:
            from services.update_service import check_for_updates

            app_info = json.loads(self.getAppInfo())
            current_version = app_info["data"]["version"]

            result = check_for_updates(current_version)
            return json.dumps({"success": True, "data": result})
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @pyqtSlot(result=str)
    def getAllReleases(self):
        """Fetch all GitHub releases"""
        try:
            from services.update_service import get_all_releases

            releases = get_all_releases()
            return json.dumps({"success": True, "data": releases})
        except Exception as e:
            logger.error(f"Error fetching releases: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @pyqtSlot(str, result=str)
    def downloadUpdate(self, save_directory):
        """Download the latest update asset to the specified directory"""
        try:
            from services.update_service import check_for_updates, download_update

            app_info = json.loads(self.getAppInfo())
            current_version = app_info["data"]["version"]

            update_info = check_for_updates(current_version)

            if not update_info["update_available"]:
                return json.dumps({"success": False, "error": "No update available"})

            if not update_info["download_url"]:
                return json.dumps({"success": False, "error": "No download available for this platform"})

            expanded_dir = os.path.expanduser(save_directory)
            os.makedirs(expanded_dir, exist_ok=True)
            save_path = os.path.join(expanded_dir, update_info["asset_name"])

            def on_progress(percent, downloaded_mb, total_mb):
                self.updateDownloadProgress.emit(json.dumps({
                    "percent": percent,
                    "downloaded_mb": downloaded_mb,
                    "total_mb": total_mb
                }))

            # Run download in background thread
            def run_download():
                try:
                    download_update(update_info["download_url"], save_path, on_progress)
                    self.updateDownloadProgress.emit(json.dumps({
                        "percent": 100,
                        "downloaded_mb": round(update_info["asset_size"] / (1024 * 1024), 1),
                        "total_mb": round(update_info["asset_size"] / (1024 * 1024), 1),
                        "completed": True,
                        "save_path": save_path
                    }))
                except Exception as e:
                    logger.error(f"Error downloading update: {e}")
                    self.updateDownloadProgress.emit(json.dumps({
                        "error": str(e)
                    }))

            thread = threading.Thread(target=run_download, daemon=True)
            thread.start()

            return json.dumps({"success": True, "message": "Download started"})
        except Exception as e:
            logger.error(f"Error starting update download: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @pyqtSlot(str, result=str)
    def openDownloadedUpdate(self, file_path):
        """Open the downloaded update file with the OS default handler"""
        try:
            import subprocess
            expanded_path = os.path.expanduser(file_path)

            if not os.path.exists(expanded_path):
                return json.dumps({"success": False, "error": "File not found"})

            if sys.platform == 'darwin':
                subprocess.Popen(['open', expanded_path])
            elif sys.platform == 'win32':
                os.startfile(expanded_path)
            else:
                subprocess.Popen(['xdg-open', expanded_path])

            logger.info(f"Opened update file: {expanded_path}")
            return json.dumps({"success": True})
        except Exception as e:
            logger.error(f"Error opening update file: {e}")
            return json.dumps({"success": False, "error": str(e)})

    def emit_sync_status(self, status_dict):
        """Emit sync status update to JavaScript"""
        self.syncStatusUpdated.emit(json.dumps(status_dict))

    def emit_sync_progress(self, progress_dict):
        """Emit sync progress update to JavaScript"""
        self.syncProgressUpdated.emit(json.dumps(progress_dict))

    # ==================== SYSTEM LOG METHODS ====================

    @pyqtSlot(result=str)
    def getSystemLogFiles(self):
        """Get list of available system log files"""
        try:
            if not LOG_DIR or not os.path.exists(LOG_DIR):
                return json.dumps({"success": True, "data": []})

            files = []
            for filename in sorted(os.listdir(LOG_DIR), reverse=True):
                if filename.endswith('.log'):
                    filepath = os.path.join(LOG_DIR, filename)
                    files.append({
                        "filename": filename,
                        "date": filename.replace('.log', ''),
                        "size": os.path.getsize(filepath)
                    })

            return json.dumps({"success": True, "data": files})
        except Exception as e:
            logger.error(f"Error getting system log files: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @pyqtSlot(str, result=str)
    def getSystemLogContent(self, filename):
        """Get content of a specific log file (last 500 lines)"""
        try:
            if not LOG_DIR:
                return json.dumps({"success": False, "error": "Log directory not configured"})

            # Sanitize filename to prevent directory traversal
            safe_filename = os.path.basename(filename)
            if not safe_filename.endswith('.log'):
                return json.dumps({"success": False, "error": "Invalid log file"})

            filepath = os.path.join(LOG_DIR, safe_filename)

            if not os.path.exists(filepath):
                return json.dumps({"success": False, "error": "Log file not found"})

            # Read last 500 lines
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                last_lines = lines[-500:] if len(lines) > 500 else lines
                content = ''.join(last_lines)

            return json.dumps({
                "success": True,
                "data": {
                    "filename": safe_filename,
                    "content": content,
                    "total_lines": len(lines),
                    "showing_lines": len(last_lines)
                }
            })
        except Exception as e:
            logger.error(f"Error reading system log: {e}")
            return json.dumps({"success": False, "error": str(e)})
