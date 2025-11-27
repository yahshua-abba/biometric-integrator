"""
Mock YAHSHUA Cloud Payroll Server for Testing
Simulates the cloud payroll API responses for development and testing
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import random
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
import hashlib

# Simulated latency in seconds
LATENCY_MIN = 0.5
LATENCY_MAX = 1.5

# Mock employees (simulating what would be in the cloud payroll)
MOCK_EMPLOYEES = [
    {"employee_code": "101", "name": "Juan Dela Cruz"},
    {"employee_code": "102", "name": "Maria Santos"},
    {"employee_code": "103", "name": "Pedro Reyes"},
    {"employee_code": "104", "name": "Ana Garcia"},
    {"employee_code": "105", "name": "Jose Rizal"},
    {"employee_code": "106", "name": "Carmen Lopez"},
    {"employee_code": "107", "name": "Miguel Torres"},
    {"employee_code": "108", "name": "Rosa Martinez"},
    {"employee_code": "109", "name": "Carlos Ramos"},
    {"employee_code": "110", "name": "Elena Cruz"},
]

# Store for auth
VALID_TOKEN = None
LOGGED_IN_USER = None


class MockYAHSHUAHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[MockServer] {format % args}")

    def simulate_latency(self):
        """Add random delay to simulate network latency"""
        delay = random.uniform(LATENCY_MIN, LATENCY_MAX)
        time.sleep(delay)

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def check_auth(self):
        """Check Bearer token authorization"""
        auth_header = self.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer ') or auth_header[7:] != VALID_TOKEN:
            self.send_json({"success": False, "message": "Unauthorized"}, 401)
            return False
        return True

    def do_GET(self):
        self.simulate_latency()
        parsed = urlparse(self.path)
        path = parsed.path

        # Health check (no auth needed)
        if path == '/api/health':
            self.send_json({"status": "ok", "server": "Mock YAHSHUA Server"})
            return

        # All other GET endpoints require auth
        if not self.check_auth():
            return

        self.send_json({"success": False, "message": "Not found"}, 404)

    def do_POST(self):
        self.simulate_latency()
        global VALID_TOKEN, LOGGED_IN_USER

        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else '{}'

        try:
            data = json.loads(body)
        except:
            data = {}

        # Login endpoint (no auth needed)
        if path == '/api/auth/login':
            self.handle_login(data)
            return

        # All other POST endpoints require auth
        if not self.check_auth():
            return

        # Timesheet sync endpoint
        if path == '/api/timesheets/sync' or path == '/api/timesheet/bulk':
            self.handle_timesheet_sync(data)
            return

        self.send_json({"success": False, "message": "Not found"}, 404)

    def handle_login(self, data):
        """Handle YAHSHUA login"""
        global VALID_TOKEN, LOGGED_IN_USER

        email = data.get('email', '')
        password = data.get('password', '')

        print(f"[MockServer] Login attempt: {email}")

        # Accept any credentials for testing
        if email and password:
            VALID_TOKEN = hashlib.md5(f"{email}{datetime.now()}".encode()).hexdigest()
            LOGGED_IN_USER = email.split('@')[0].title()

            print(f"[MockServer] Login successful: {LOGGED_IN_USER}")

            self.send_json({
                "success": True,
                "token": VALID_TOKEN,
                "user_logged": LOGGED_IN_USER,
                "message": "Login successful"
            })
        else:
            self.send_json({
                "success": False,
                "message": "Invalid credentials"
            }, 401)

    def handle_timesheet_sync(self, data):
        """Handle timesheet sync (push) from the integration tool"""
        timesheets = data.get('timesheets', [])

        if not timesheets:
            self.send_json({
                "success": False,
                "message": "No timesheets provided"
            }, 400)
            return

        print(f"[MockServer] Receiving {len(timesheets)} timesheet records")

        # Simulate processing each timesheet
        results = []
        success_count = 0
        failed_count = 0

        for ts in timesheets:
            # Randomly fail some records for testing (10% failure rate)
            if random.random() < 0.1:
                results.append({
                    "sync_id": ts.get('sync_id'),
                    "success": False,
                    "error": "Employee not found in payroll system"
                })
                failed_count += 1
            else:
                # Generate a mock backend ID
                backend_id = random.randint(10000, 99999)
                results.append({
                    "sync_id": ts.get('sync_id'),
                    "success": True,
                    "backend_timesheet_id": backend_id
                })
                success_count += 1

        print(f"[MockServer] Processed: {success_count} success, {failed_count} failed")

        self.send_json({
            "success": True,
            "message": f"Processed {len(timesheets)} records",
            "results": results,
            "summary": {
                "total": len(timesheets),
                "success": success_count,
                "failed": failed_count
            }
        })


def generate_dummy_attendance(date_from=None, date_to=None, num_records=100):
    """
    Generate dummy attendance data for testing
    Similar to the old PyQt version's get_dummy_data function
    """
    dummy_data = []

    if date_from is None:
        date_from = datetime.now() - timedelta(days=7)
    if date_to is None:
        date_to = datetime.now()

    if isinstance(date_from, str):
        date_from = datetime.strptime(date_from, "%Y-%m-%d")
    if isinstance(date_to, str):
        date_to = datetime.strptime(date_to, "%Y-%m-%d")

    for i in range(num_records):
        # Random timestamp within date range
        delta = date_to - date_from
        random_seconds = random.randint(0, int(delta.total_seconds()))
        timestamp = date_from + timedelta(seconds=random_seconds)

        # Random employee
        employee = random.choice(MOCK_EMPLOYEES)

        # Alternate IN/OUT based on index
        log_type = "out" if i % 2 else "in"

        attendance = {
            "user_id": employee["employee_code"],
            "name": employee["name"],
            "timestamp": timestamp,
            "date": timestamp.strftime("%Y-%m-%d"),
            "time": timestamp.strftime("%H:%M:%S"),
            "log_type": log_type,
            "punch": i % 6,  # 0-5 punch types
        }

        dummy_data.append(attendance)

    # Sort by timestamp
    dummy_data.sort(key=lambda x: x["timestamp"])

    return dummy_data


def run_mock_server(port=8080):
    """Run the mock YAHSHUA server"""
    server = HTTPServer(('localhost', port), MockYAHSHUAHandler)

    print("=" * 60)
    print(f"  Mock YAHSHUA Cloud Payroll Server")
    print(f"  Running on http://localhost:{port}")
    print("=" * 60)
    print(f"\nEndpoints:")
    print(f"  POST /api/auth/login        - Login (any email/password)")
    print(f"  POST /api/timesheets/sync   - Push timesheets")
    print(f"  GET  /api/health            - Health check")
    print(f"\nConfigure the app with:")
    print(f"  Push URL: http://localhost:{port}")
    print(f"  Username: test@example.com")
    print(f"  Password: test123")
    print(f"\nPress Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down mock server...")
        server.shutdown()


def seed_database(num_records=50, device_id=None):
    """
    Seed the SQLite database with dummy attendance data.
    This inserts records directly into the timesheet table for testing.
    """
    from database import Database

    db = Database()

    # If no device_id specified, try to get the first enabled device
    if device_id is None:
        devices = db.get_enabled_devices()
        if devices:
            device_id = devices[0]['id']
            print(f"Using device: {devices[0]['name']} (ID: {device_id})")
        else:
            print("Warning: No devices found. Creating a test device...")
            device_id = db.add_device("Test Device", "192.168.1.100", 4370)
            print(f"Created test device with ID: {device_id}")

    # Generate dummy data
    data = generate_dummy_attendance(num_records=num_records)

    print(f"Seeding database with {len(data)} records...")

    inserted = 0
    skipped = 0

    for record in data:
        # Create sync_id matching the format used by pull_service
        sync_id = f"ZK_{device_id}_{record['user_id']}_{record['timestamp'].strftime('%Y%m%d%H%M%S')}"

        # Check if employee exists, create if not
        employee = db.get_employee_by_backend_id(record['user_id'])
        if not employee:
            db.add_or_update_employee(
                backend_id=record['user_id'],
                name=record['name'],
                employee_code=record['user_id']
            )
            employee = db.get_employee_by_backend_id(record['user_id'])

        # Check if timesheet already exists
        existing = db.get_timesheet_by_sync_id(sync_id)
        if existing:
            skipped += 1
            continue

        # Insert timesheet
        db.add_timesheet_entry(
            sync_id=sync_id,
            employee_id=employee['id'],
            log_type=record['log_type'],
            date=record['date'],
            time=record['time'],
            device_id=device_id
        )
        inserted += 1

    print(f"Done! Inserted: {inserted}, Skipped (duplicates): {skipped}")
    return inserted


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--generate':
        # Generate dummy data for testing (console only)
        print("Generating dummy attendance data (console preview only)...")
        data = generate_dummy_attendance(num_records=50)
        for record in data[:10]:
            print(f"  {record['date']} {record['time']} - {record['name']} ({record['user_id']}) - {record['log_type'].upper()}")
        print(f"  ... and {len(data) - 10} more records")
        print("\nTo insert into database, use: python mock_server.py --seed")

    elif len(sys.argv) > 1 and sys.argv[1] == '--seed':
        # Seed the database with dummy data
        num_records = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        seed_database(num_records=num_records)

    elif len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("Mock YAHSHUA Server - Usage:")
        print("")
        print("  python mock_server.py              Run the mock server on port 8080")
        print("  python mock_server.py 9000         Run the mock server on port 9000")
        print("  python mock_server.py --seed       Seed database with 50 dummy records")
        print("  python mock_server.py --seed 100   Seed database with 100 dummy records")
        print("  python mock_server.py --generate   Preview dummy data (console only)")
        print("  python mock_server.py --help       Show this help message")

    else:
        # Run the mock server
        port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
        run_mock_server(port)
