"""
Biometric Integration - Push Service
Service for pushing timesheet data to cloud payroll systems
"""

import requests
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# YAHSHUA API endpoints (default, can be overridden via config)
DEFAULT_YAHSHUA_BASE_URL = "https://yahshuapayroll.com/api"

# User-friendly messages for YAHSHUA error codes
YAHSHUA_ERROR_MESSAGES = {
    100: "Invalid request format",
    101: "Missing required field",
    102: "Invalid date format",
    103: "Invalid time format",
    110: "Invalid employee code",
    120: "Duplicate record already exists",
    130: "Branch not found",
    140: "Employee not found in payroll system",
    141: "Employee is inactive",
    142: "Employee not assigned to branch",
    143: "Employee not recognized in payroll system",
    150: "Invalid log type",
    160: "Record outside allowed date range",
    200: "Server processing error",
    500: "Payroll server internal error",
}

# User-friendly messages for HTTP status codes
HTTP_ERROR_MESSAGES = {
    400: "Bad request - the data sent was invalid",
    401: "Authentication expired - please log in again",
    403: "Access denied - insufficient permissions",
    404: "Payroll API endpoint not found - check your URL configuration",
    408: "Request timed out - the server took too long to respond",
    429: "Too many requests - please wait before trying again",
    500: "Payroll server error - please try again later",
    502: "Payroll server is temporarily unavailable",
    503: "Payroll service is under maintenance",
    504: "Payroll server timed out",
}


def get_friendly_yahshua_error(error_code, reason):
    """Get a user-friendly error message for a YAHSHUA error code"""
    friendly = YAHSHUA_ERROR_MESSAGES.get(error_code)
    if friendly:
        return friendly
    # Fall back to the reason from the API if no mapping exists
    if reason and reason != 'Unknown error':
        return reason
    return f"Sync failed (error code {error_code})"


def get_friendly_http_error(status_code):
    """Get a user-friendly error message for an HTTP status code"""
    friendly = HTTP_ERROR_MESSAGES.get(status_code)
    if friendly:
        return friendly
    if 400 <= status_code < 500:
        return f"Request error ({status_code}) - check your configuration"
    if 500 <= status_code < 600:
        return f"Payroll server error ({status_code}) - please try again later"
    return f"Unexpected response from payroll server ({status_code})"


class PushService:
    """Service for pushing data to YAHSHUA Payroll cloud system"""

    def __init__(self, database):
        self.database = database
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Biometric Integration/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })

    def get_base_url(self):
        """Get the YAHSHUA API base URL from config or use default"""
        config = self.database.get_api_config()
        url = (config or {}).get('push_url') or DEFAULT_YAHSHUA_BASE_URL
        return url.rstrip('/')

    def get_config(self):
        """Get push configuration from database"""
        config = self.database.get_api_config()
        if not config:
            raise Exception("API configuration not found")

        if not config.get('push_username') or not config.get('push_password'):
            raise Exception("YAHSHUA credentials not configured")

        return config

    def authenticate(self, username=None, password=None):
        """
        Authenticate with YAHSHUA Payroll and get token

        Args:
            username: Optional username (uses config if not provided)
            password: Optional password (uses config if not provided)

        Returns:
            dict: Authentication response with token, user_logged, company_name
        """
        try:
            if not username or not password:
                config = self.get_config()
                username = config.get('push_username')
                password = config.get('push_password')

            logger.info(f"Authenticating to YAHSHUA as {username}")

            payload = {
                "username": username,
                "password": password
            }

            # YAHSHUA API requires credentials in both query params and body
            base_url = self.get_base_url()
            login_url = f"{base_url}/api-auth/"

            response = self.session.post(
                login_url,
                params={"username": username, "password": password},
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                token = data.get('token')
                user_logged = data.get('user_logged')
                company_name = data.get('company_name')

                if not token:
                    raise Exception("No token in response")

                # Store token and user info in database
                self.database.update_push_token(token, user_logged)

                logger.info(f"YAHSHUA authentication successful. User: {user_logged}, Company: {company_name}")
                return {
                    'token': token,
                    'user_logged': user_logged,
                    'company_name': company_name
                }

            elif response.status_code == 401:
                error_data = response.json()
                error_msg = error_data.get('message', 'Invalid credentials')
                raise Exception(f"Login failed: {error_msg}")

            else:
                friendly = get_friendly_http_error(response.status_code)
                raise Exception(f"Login failed: {friendly}")

        except requests.exceptions.Timeout:
            raise Exception("Login timed out - the payroll server is not responding")
        except requests.exceptions.ConnectionError:
            raise Exception("Cannot connect to the payroll server - check your internet connection and URL")
        except Exception as e:
            logger.error(f"YAHSHUA authentication error: {e}")
            raise

    def get_valid_token(self):
        """Get a valid token, authenticating if necessary"""
        token = self.database.get_push_token()

        if token:
            logger.info("Using existing YAHSHUA token")
            return token

        logger.info("No valid token found, authenticating...")
        auth_result = self.authenticate()
        return auth_result['token']

    def test_connection(self):
        """Test connection to YAHSHUA Payroll API"""
        try:
            auth_result = self.authenticate()
            return True, f"Connection successful. Logged in as {auth_result['user_logged']}"
        except Exception as e:
            return False, str(e)

    def push_data(self, progress_callback=None):
        """
        Push unsynced timesheet data to YAHSHUA Payroll in batches of 50

        Args:
            progress_callback: Optional callback function for progress updates.
                              Called with dict: {batch_current, batch_total, batch_size, success, failed}

        Returns:
            tuple: (success: bool, message: str, stats: dict)
        """
        BATCH_SIZE = 50

        log_id = self.database.create_sync_log('push')
        stats = {
            'processed': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'batches_completed': 0,
            'batches_total': 0
        }

        try:
            logger.info("Starting push sync to YAHSHUA Payroll")

            # Get token
            token = self.get_valid_token()

            # Get ALL unsynced timesheets
            all_unsynced = self.database.get_unsynced_timesheets(limit=10000)
            logger.info(f"Found {len(all_unsynced)} unsynced timesheet records")

            if len(all_unsynced) == 0:
                message = "No records to sync"
                logger.info(message)
                self.database.update_sync_log(
                    log_id, status='success', records_processed=0
                )
                return True, message, stats

            # Build log_list for all valid records
            all_log_entries = []
            timesheet_map = {}  # Map local ID to timesheet data

            for timesheet in all_unsynced:
                stats['processed'] += 1

                # Get employee code
                employee_code = timesheet.get('employee_code')
                if not employee_code:
                    logger.warning(f"Timesheet {timesheet['id']} has no employee code, skipping")
                    stats['skipped'] += 1
                    continue

                # Transform to YAHSHUA format
                log_entry = {
                    "id": timesheet['id'],
                    "employee": employee_code,  # Employee code from ZKTeco device
                    "log_time": timesheet['time'],  # HH:MM format
                    "log_type": timesheet['log_type'].upper(),  # IN or OUT
                    "sync_id": timesheet['sync_id'],
                    "date": timesheet['date']  # YYYY-MM-DD format
                }

                # Include branch_id if available (from device configuration)
                branch_id = timesheet.get('branch_id')
                if branch_id:
                    log_entry["branch_id"] = branch_id

                all_log_entries.append(log_entry)
                timesheet_map[timesheet['id']] = timesheet

            if len(all_log_entries) == 0:
                message = "No valid records to sync"
                logger.info(message)
                self.database.update_sync_log(
                    log_id, status='success', records_processed=stats['processed']
                )
                return True, message, stats

            # Split into batches of 50
            batches = []
            for i in range(0, len(all_log_entries), BATCH_SIZE):
                batches.append(all_log_entries[i:i + BATCH_SIZE])

            stats['batches_total'] = len(batches)
            logger.info(f"Split {len(all_log_entries)} records into {len(batches)} batches of up to {BATCH_SIZE}")

            batch_error = None

            # Process each batch
            for batch_num, batch in enumerate(batches, 1):
                logger.info(f"Processing batch {batch_num}/{len(batches)} ({len(batch)} records)")

                # Emit progress before processing batch
                if progress_callback:
                    progress_callback({
                        'batch_current': batch_num,
                        'batch_total': len(batches),
                        'batch_size': len(batch),
                        'success': stats['success'],
                        'failed': stats['failed']
                    })

                # Push batch to YAHSHUA
                success, result = self.push_batch(token, batch)

                if success:
                    # Process results for this batch
                    logs_synced = result.get('logs_successfully_sync', [])
                    logs_failed = result.get('logs_not_sync', [])

                    # Mark successful logs
                    for local_id in logs_synced:
                        self.database.mark_timesheet_synced(local_id, local_id)
                        stats['success'] += 1
                        logger.info(f"Timesheet {local_id} synced successfully")

                    # Mark failed logs with reason (individual record failures)
                    for failed_log in logs_failed:
                        local_id = failed_log.get('id')
                        reason = failed_log.get('reason', 'Unknown error')
                        error_code = failed_log.get('error_code', 0)

                        friendly_msg = get_friendly_yahshua_error(error_code, reason)
                        self.database.mark_timesheet_sync_failed(local_id, friendly_msg)
                        stats['failed'] += 1
                        logger.warning(f"Timesheet {local_id} failed (code {error_code}): {reason} -> {friendly_msg}")

                    stats['batches_completed'] += 1
                    logger.info(f"Batch {batch_num} completed: {len(logs_synced)} synced, {len(logs_failed)} failed")

                else:
                    # Batch-level failure (network error, timeout) - STOP immediately
                    batch_error = result.get('error', 'Unknown error')
                    logger.error(f"Batch {batch_num} failed: {batch_error} - stopping")

                    # Mark all records in this batch as failed
                    for log_entry in batch:
                        self.database.mark_timesheet_sync_failed(
                            log_entry['id'],
                            batch_error
                        )
                        stats['failed'] += 1

                    break  # Stop processing remaining batches

            # Emit final progress (completed)
            if progress_callback:
                progress_callback({
                    'batch_current': stats['batches_completed'],
                    'batch_total': stats['batches_total'],
                    'batch_size': 0,
                    'success': stats['success'],
                    'failed': stats['failed'],
                    'completed': True
                })

            # Update last push time
            self.database.update_last_sync_time('push')

            # Update sync log
            status = 'success' if batch_error is None and stats['failed'] == 0 else 'error'
            self.database.update_sync_log(
                log_id,
                status=status,
                records_processed=stats['processed'],
                records_success=stats['success'],
                records_failed=stats['failed']
            )

            # Build message
            if batch_error:
                message = f"Push failed: {batch_error}"
                if stats['success'] > 0:
                    message += f" ({stats['success']} synced before error, {stats['failed']} failed)"
            elif stats['failed'] > 0:
                message = f"Push completed with errors: {stats['success']} synced, {stats['failed']} failed"
            else:
                message = f"Push completed: {stats['success']} records synced successfully"

            logger.info(message)
            return batch_error is None, message, stats

        except Exception as e:
            error_msg = f"Push sync error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.database.update_sync_log(
                log_id, 'error', error_message=error_msg
            )
            return False, error_msg, stats

    def push_batch(self, token, log_list):
        """
        Push a batch of logs to YAHSHUA

        Args:
            token: YAHSHUA auth token
            log_list: List of log entries in YAHSHUA format

        Returns:
            tuple: (success: bool, result: dict)
        """
        try:
            headers = {
                'Authorization': f'Token {token}'
            }

            # YAHSHUA API requires:
            # - from_biometrics: true to extract log_list from wrapper
            # - from_new_biometrics: true to lookup by employee code (not PK)
            payload = {
                "from_biometrics": True,
                "from_new_biometrics": True,
                "log_list": log_list
            }

            base_url = self.get_base_url()
            sync_url = f"{base_url}/sync-time-in-out/"

            logger.info(f"Pushing {len(log_list)} logs to YAHSHUA")
            logger.debug(f"Payload: {json.dumps(payload, indent=2)}")

            response = self.session.post(
                sync_url,
                headers=headers,
                json=payload,
                timeout=60
            )

            data = response.json()
            logger.info(f"YAHSHUA response: {json.dumps(data)}")

            if response.status_code == 200:
                # Success or partial success
                return True, data

            elif response.status_code == 400:
                # Bad request - check for partial success
                if data.get('logs_successfully_sync'):
                    return True, data
                return False, {'error': data.get('message', 'Bad request')}

            elif response.status_code == 401:
                # Token expired, try to re-authenticate
                logger.warning("Token expired, re-authenticating...")
                self.database.update_push_token(None)
                new_token = self.authenticate()
                # Retry once with new token
                headers['Authorization'] = f'Token {new_token}'
                retry_response = self.session.post(
                    sync_url,
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                if retry_response.status_code == 200:
                    return True, retry_response.json()
                friendly = get_friendly_http_error(retry_response.status_code)
                logger.error(f"Retry after re-auth failed: HTTP {retry_response.status_code}")
                return False, {'error': f'Authentication failed after retry: {friendly}'}

            else:
                friendly = get_friendly_http_error(response.status_code)
                logger.error(f"Push batch failed: HTTP {response.status_code} - {response.text[:200]}")
                return False, {'error': friendly}

        except requests.exceptions.Timeout:
            return False, {'error': 'Request timed out - the payroll server took too long to respond'}
        except requests.exceptions.ConnectionError:
            return False, {'error': 'Cannot connect to the payroll server - check your internet connection'}
        except Exception as e:
            return False, {'error': str(e)}

    def invalidate_token(self):
        """Invalidate the current token (force re-authentication)"""
        self.database.update_push_token(None)
        logger.info("Push token invalidated")
