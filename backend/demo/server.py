"""Mini Payroll and before/after demo. Run: python backend/demo/server.py.

Only synthetic data and loopback URLs are used. The old-behavior adapter disables
duplicate suppression; the fixed lane uses the production PushService unchanged.
Payroll intentionally forgets a deleted punch to expose the client's retry bug.
This is a test contract, not a claim about the actual Payroll deletion API.
"""

import argparse
import json
import logging
import sys
import tempfile
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database import Database
from services.push_service import PushService


class LegacyPushService(PushService):
    """Reproduce the old retry decision, isolated from the shipping application."""

    def _is_duplicate_error(self, error_code, reason):
        return False


class Lane:
    def __init__(self, mode, directory, base_url):
        self.mode = mode
        self.db = Database(str(directory / f'{mode}.db'))
        self.db.add_or_update_employee('4472', 'Mara Santos (demo)', '4472')
        self.employee = self.db.get_employee_by_code('4472')['id']
        self.sync_id = 'ZK_DEMO_4472_20260824185200'
        self.db.add_timesheet_entry(self.sync_id, self.employee, 'in', '2026-08-24', '18:52:00')
        self.db.update_api_config(
            push_url=f'{base_url}/payroll/{mode}/api',
            push_username='demo', push_password='demo',
            push_url_2=f'{base_url}/payroll/{mode}/api',
            push_username_2='demo', push_password_2='demo', push_enabled_2=1,
        )
        cls = LegacyPushService if mode == 'before' else PushService
        self.services = [cls(self.db, slot) for slot in (1, 2)]
        self.payroll = {}
        self.events = []
        self.requests = 0
        self.deleted = False
        self.lock = threading.Lock()
        self.record('Ready', 'One synthetic tap. Two configurations reach the same mini Payroll.')

    def record(self, event, detail):
        self.events.append({'time': datetime.now().strftime('%H:%M:%S'), 'event': event, 'detail': detail})
        self.events = self.events[-80:]

    def sync(self):
        # Ordered so every reset reproduces the same winning destination.
        # The actual PushService still performs real HTTP requests below.
        for svc in self.services:
            _, message, _ = svc.push_data()
            with self.lock:
                self.record(f'Payroll {svc.slot} sync', message)

    def delete(self):
        with self.lock:
            count = len(self.payroll)
            self.payroll.clear()
            self.deleted = self.deleted or count > 0
            self.record('Deletion approved', f'HR deleted {count} attendance record(s) from mini Payroll.')

    def receive(self, rows):
        success, failed = [], []
        with self.lock:
            self.requests += 1
            for row in rows:
                key = row['sync_id']
                if key in self.payroll:
                    failed.append({'id': row['id'], 'error_code': 120, 'reason': 'Duplicate record already exists'})
                    self.record('HTTP · duplicate rejected', f"{row['employee']} · {row['log_time']} · {key}")
                else:
                    self.payroll[key] = dict(row)
                    success.append(row['id'])
                    self.record('HTTP · punch recreated' if self.deleted else 'HTTP · punch accepted',
                                f"{row['employee']} · {row['date']} · {row['log_time']} {row['log_type']}")
        return (400 if failed and not success else 200), {'logs_successfully_sync': success, 'logs_not_sync': failed}

    def snapshot(self):
        with self.lock:
            row = self.db.get_all_timesheets()[0]
            slots = []
            for slot in (1, 2):
                suffix = '_2' if slot == 2 else ''
                reason = row[f'sync_skipped_reason{suffix}'] or row[f'sync_error_message{suffix}']
                status = 'Synced' if row[f'backend_timesheet_id{suffix}'] is not None else (
                    'Duplicate skipped' if row[f'sync_skipped_reason{suffix}'] else 'Retry queued' if reason else 'Pending')
                slots.append({'slot': slot, 'status': status, 'reason': reason})
            return {'mode': self.mode, 'slots': slots, 'payroll': list(self.payroll.values()),
                    'requests': self.requests, 'deleted': self.deleted, 'events': list(reversed(self.events)),
                    'sync_id': self.sync_id}


class Demo:
    def __init__(self, base_url):
        self.base_url = base_url
        self.control_lock = threading.RLock()
        self.stop = threading.Event()
        self.automatic = False
        self.next_sync = None
        self.directory = None
        self.lanes = {}
        self.reset()
        self.thread = threading.Thread(target=self._auto_loop, daemon=True)
        self.thread.start()

    def reset(self):
        with self.control_lock:
            self.automatic = False
            self.next_sync = None
            for lane in self.lanes.values():
                for service in lane.services:
                    service.session.close()
            if self.directory:
                self.directory.cleanup()
            self.directory = tempfile.TemporaryDirectory(prefix='biometric-demo-')
            self.lanes = {mode: Lane(mode, Path(self.directory.name), self.base_url) for mode in ('before', 'after')}

    def action(self, action):
        with self.control_lock:
            if action == 'reset':
                self.reset()
            elif action == 'sync':
                for lane in self.lanes.values():
                    lane.sync()
            elif action == 'delete':
                for lane in self.lanes.values():
                    lane.delete()
            elif action == 'auto':
                self.automatic = not self.automatic
                self.next_sync = time.monotonic() + 5 if self.automatic else None
            else:
                raise ValueError('Unknown demo action')

    def snapshot(self):
        with self.control_lock:
            return {'automatic': self.automatic, 'interval': 5,
                    'countdown': max(0, round(self.next_sync - time.monotonic(), 1)) if self.next_sync else None,
                    'lanes': [lane.snapshot() for lane in self.lanes.values()]}

    def _auto_loop(self):
        while not self.stop.wait(0.2):
            with self.control_lock:
                if self.automatic and time.monotonic() >= self.next_sync:
                    self.action('sync')
                    self.next_sync = time.monotonic() + 5

    def close(self):
        self.stop.set()
        self.thread.join(timeout=10)
        for lane in self.lanes.values():
            for service in lane.services:
                service.session.close()
        self.directory.cleanup()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_json(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/state':
            self.send_json(200, self.server.demo.snapshot())
        elif path == '/':
            body = Path(__file__).with_name('index.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_json(404, {'error': 'Not found'})

    def do_POST(self):
        # The local demo has no reason to accept control requests from other sites.
        if self.headers.get('Origin') not in (None, self.server.demo.base_url):
            self.send_json(403, {'error': 'Use the local demo page'})
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if size < 0 or size > 65536:
                raise ValueError('Request too large')
            data = json.loads(self.rfile.read(size) or b'{}')
            path = urlparse(self.path).path
            if path == '/action':
                self.server.demo.action(data.get('action'))
                self.send_json(200, self.server.demo.snapshot())
                return
            for mode, lane in self.server.demo.lanes.items():
                base = f'/payroll/{mode}/api'
                if path == base + '/api-auth/':
                    if data.get('username') != 'demo' or data.get('password') != 'demo':
                        self.send_json(401, {'message': 'Use demo credentials'})
                    else:
                        self.send_json(200, {'token': 'demo-token', 'user_logged': 'Demo HR', 'company_name': 'Mini Payroll'})
                    return
                if path == base + '/sync-time-in-out/':
                    if self.headers.get('Authorization') != 'Token demo-token':
                        self.send_json(401, {'message': 'Unauthorized'})
                        return
                    if not data.get('from_biometrics') or not data.get('from_new_biometrics'):
                        raise ValueError('Expected biometric payload flags')
                    self.send_json(*lane.receive(data['log_list']))
                    return
            self.send_json(404, {'error': 'Not found'})
        except (ValueError, KeyError, TypeError) as error:
            self.send_json(400, {'error': str(error)})


def create_server(port=8877):
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.demo = Demo(f'http://127.0.0.1:{server.server_port}')
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8877)
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    server = create_server(args.port)
    print(f'Local demo: {server.demo.base_url} — synthetic data only', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.demo.close()
        server.server_close()


if __name__ == '__main__':
    main()
