"""
Attendance Sync - Pull Service
Pulls attendance data from ZKTeco devices via PyZk
"""

import logging
from datetime import datetime, timedelta
from zk import ZK

logger = logging.getLogger(__name__)


class PullService:
    """Service for pulling attendance data from ZKTeco device"""

    def __init__(self, database):
        self.database = database
        self.zk = None
        self.conn = None
        self.current_device_id = None

    def get_device_config(self, device_id=None):
        """Get ZKTeco device configuration from database

        Args:
            device_id: If provided, get config for specific device from device table.
                      If None, falls back to legacy api_config (for backwards compatibility).
        """
        if device_id is not None:
            device = self.database.get_device(device_id)
            if not device:
                return None, None, None
            return device.get('ip'), device.get('port', 4370), device
        else:
            # Legacy fallback to api_config
            config = self.database.get_api_config()
            if not config:
                return None, None, None
            ip = config.get('device_ip')
            port = config.get('device_port', 4370)
            return ip, port, config

    def connect(self, device_id=None):
        """Connect to ZKTeco device

        Args:
            device_id: If provided, connect to specific device.
                      If None, uses legacy api_config.
        """
        ip, port, _ = self.get_device_config(device_id)

        if not ip:
            raise Exception("Device IP not configured")

        logger.info(f"Connecting to ZKTeco device at {ip}:{port}")

        self.zk = ZK(ip, port=port, timeout=10)
        self.conn = self.zk.connect()
        self.current_device_id = device_id

        if not self.conn:
            raise Exception(f"Failed to connect to device at {ip}:{port}")

        logger.info("Connected to ZKTeco device successfully")
        return self.conn

    def disconnect(self):
        """Disconnect from ZKTeco device"""
        if self.conn:
            try:
                self.conn.disconnect()
                logger.info("Disconnected from ZKTeco device")
            except:
                pass
            self.conn = None
            self.zk = None
            self.current_device_id = None

    def test_connection(self, device_id=None):
        """Test connection to ZKTeco device

        Args:
            device_id: If provided, test specific device. If None, uses legacy api_config.
        """
        try:
            conn = self.connect(device_id)

            # Get device info
            device_name = conn.get_device_name() or "Unknown"
            serial = conn.get_serialnumber() or "Unknown"
            firmware = conn.get_firmware_version() or "Unknown"

            self.disconnect()

            return True, f"Connected! Device: {device_name}, Serial: {serial}, Firmware: {firmware}"
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            self.disconnect()
            return False, str(e)

    def pull_data(self, date_from=None, date_to=None, device_id=None, progress_callback=None):
        """
        Pull attendance data from ZKTeco device(s)

        Args:
            date_from: Start date (YYYY-MM-DD) - filter logs after this date
            date_to: End date (YYYY-MM-DD) - filter logs before this date
            device_id: If provided, pull from specific device. If None, pull from all enabled devices.
            progress_callback: Function to call with progress updates

        Returns:
            tuple: (success, message, stats)
        """
        # If device_id is None, pull from all enabled devices
        if device_id is None:
            devices = self.database.get_enabled_devices()
            if not devices:
                return False, "No enabled devices configured", {'total_logs': 0, 'processed': 0, 'new_records': 0, 'duplicates': 0, 'errors': 0, 'devices_synced': 0, 'devices_failed': 0}

            # Aggregate stats across all devices
            total_stats = {
                'total_logs': 0,
                'processed': 0,
                'new_records': 0,
                'duplicates': 0,
                'errors': 0,
                'devices_synced': 0,
                'devices_failed': 0
            }
            messages = []

            for i, device in enumerate(devices):
                if progress_callback:
                    progress_callback({
                        'type': 'pull',
                        'status': 'connecting',
                        'message': f"Syncing device {i+1} of {len(devices)}: {device['name']}",
                        'device_index': i + 1,
                        'device_total': len(devices),
                        'device_name': device['name']
                    })

                success, msg, stats = self._pull_from_device(
                    device['id'],
                    date_from,
                    date_to,
                    progress_callback
                )

                total_stats['total_logs'] += stats.get('total_logs', 0)
                total_stats['processed'] += stats.get('processed', 0)
                total_stats['new_records'] += stats.get('new_records', 0)
                total_stats['duplicates'] += stats.get('duplicates', 0)
                total_stats['errors'] += stats.get('errors', 0)

                if success:
                    total_stats['devices_synced'] += 1
                    messages.append(f"{device['name']}: {msg}")
                else:
                    total_stats['devices_failed'] += 1
                    messages.append(f"{device['name']}: FAILED - {msg}")

            overall_success = total_stats['devices_synced'] > 0
            summary = f"Pull complete: {total_stats['devices_synced']}/{len(devices)} devices synced, {total_stats['new_records']} new records"
            if total_stats['devices_failed'] > 0:
                summary += f", {total_stats['devices_failed']} device(s) failed"

            return overall_success, summary, total_stats

        else:
            # Pull from specific device
            return self._pull_from_device(device_id, date_from, date_to, progress_callback)

    def _pull_from_device(self, device_id, date_from=None, date_to=None, progress_callback=None):
        """
        Pull attendance data from a specific ZKTeco device

        Args:
            device_id: The device ID to pull from
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            progress_callback: Function to call with progress updates

        Returns:
            tuple: (success, message, stats)
        """
        stats = {
            'total_logs': 0,
            'processed': 0,
            'new_records': 0,
            'duplicates': 0,
            'errors': 0
        }

        # Get device info for logging
        device = self.database.get_device(device_id)
        device_name = device['name'] if device else f"Device {device_id}"

        # Parse date range
        if date_from:
            start_date = datetime.strptime(date_from, "%Y-%m-%d")
        else:
            start_date = datetime.now() - timedelta(days=1)

        if date_to:
            end_date = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        else:
            end_date = datetime.now().replace(hour=23, minute=59, second=59)

        logger.info(f"Pulling attendance from {device_name} ({start_date} to {end_date})")

        # Create sync log
        log_id = self.database.create_sync_log('pull')

        try:
            # Connect to device
            if progress_callback:
                progress_callback({
                    'type': 'pull',
                    'status': 'connecting',
                    'message': f'Connecting to {device_name}...',
                    'device_name': device_name
                })

            conn = self.connect(device_id)

            # Get all attendance records
            if progress_callback:
                progress_callback({
                    'type': 'pull',
                    'status': 'fetching',
                    'message': f'Fetching attendance logs from {device_name}...',
                    'device_name': device_name
                })

            attendance = conn.get_attendance()
            stats['total_logs'] = len(attendance)

            logger.info(f"Retrieved {len(attendance)} total attendance logs from {device_name}")

            # Get users for employee mapping
            users = conn.get_users()
            user_map = {str(u.user_id): u.name for u in users}

            logger.info(f"Retrieved {len(users)} users from {device_name}")

            # Sync users to employee table
            for user in users:
                self.database.add_or_update_employee(
                    backend_id=str(user.user_id),
                    name=user.name or f"User {user.user_id}",
                    employee_code=str(user.user_id)
                )

            # Process attendance logs
            for i, log in enumerate(attendance):
                try:
                    # Filter by date range
                    if log.timestamp < start_date or log.timestamp > end_date:
                        continue

                    stats['processed'] += 1

                    # Determine punch type (0=IN, 1=OUT, or based on device config)
                    # Some devices use: 0=Check-In, 1=Check-Out, 2=Break-Out, 3=Break-In, 4=OT-In, 5=OT-Out
                    punch = getattr(log, 'punch', 0) or 0
                    if punch in [0, 3, 4]:  # IN types
                        log_type = 'in'
                    else:  # OUT types
                        log_type = 'out'

                    # Create unique sync_id (includes device_id for uniqueness across devices)
                    date_str = log.timestamp.strftime("%Y-%m-%d")
                    time_str = log.timestamp.strftime("%H:%M:%S")
                    sync_id = f"ZK_{device_id}_{log.user_id}_{log.timestamp.strftime('%Y%m%d%H%M%S')}"

                    # Get employee from database
                    employee = self.database.get_employee_by_code(str(log.user_id))
                    if not employee:
                        logger.warning(f"Employee not found for user_id: {log.user_id}")
                        stats['errors'] += 1
                        continue

                    # Add to database with device_id
                    result = self.database.add_timesheet_entry(
                        sync_id=sync_id,
                        employee_id=employee['id'],
                        log_type=log_type,
                        date=date_str,
                        time=time_str,
                        device_id=device_id
                    )

                    if result:
                        stats['new_records'] += 1
                        logger.debug(f"Added: {employee.get('name', 'Unknown')} - {date_str} {time_str} - {log_type}")
                    else:
                        stats['duplicates'] += 1

                    # Progress update
                    if progress_callback and stats['processed'] % 50 == 0:
                        progress_callback({
                            'type': 'pull',
                            'status': 'processing',
                            'records_fetched': stats['total_logs'],
                            'records_processed': stats['processed'],
                            'records_success': stats['new_records'],
                            'device_name': device_name
                        })

                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"Error processing log: {e}")

            self.disconnect()

            # Update sync log with device metadata
            self.database.update_sync_log(
                log_id,
                status='success',
                records_processed=stats['processed'],
                records_success=stats['new_records'],
                records_failed=stats['errors'],
                metadata={'device_id': device_id, 'device_name': device_name}
            )

            # Update device last pull timestamp
            self.database.update_device_last_pull(device_id)

            # Also update global last pull timestamp for backwards compatibility
            self.database.update_api_config(last_pull_at=datetime.now().isoformat())

            message = f"{stats['new_records']} new, {stats['duplicates']} duplicates, {stats['errors']} errors"
            logger.info(f"Pull from {device_name} complete: {message}")

            return True, message, stats

        except Exception as e:
            logger.error(f"Pull from {device_name} failed: {e}", exc_info=True)
            self.disconnect()

            self.database.update_sync_log(
                log_id,
                status='error',
                error_message=str(e),
                metadata={'device_id': device_id, 'device_name': device_name}
            )

            return False, str(e), stats

    def get_device_users(self):
        """Get list of users from ZKTeco device"""
        try:
            conn = self.connect()
            users = conn.get_users()
            self.disconnect()

            return [{
                'user_id': u.user_id,
                'name': u.name,
                'privilege': u.privilege,
                'card': getattr(u, 'card', None)
            } for u in users]

        except Exception as e:
            logger.error(f"Failed to get users: {e}")
            self.disconnect()
            raise

    def clear_device_attendance(self):
        """Clear attendance logs from device (use with caution!)"""
        try:
            conn = self.connect()
            conn.clear_attendance()
            self.disconnect()
            logger.info("Cleared attendance logs from device")
            return True, "Attendance logs cleared from device"
        except Exception as e:
            logger.error(f"Failed to clear attendance: {e}")
            self.disconnect()
            return False, str(e)
