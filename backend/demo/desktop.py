"""Open the real biometric desktop app with isolated mini Payroll test data.

Build frontend/dist first, then: python backend/demo/desktop.py --large
Requires the normal desktop dependencies (including Qt); no real devices or
Payroll credentials are loaded. Closing the app discards its temporary database.
"""
import argparse
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from demo.server import create_server
from demo.fixtures import seed_large_queue


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--large', action='store_true', help='Add 300 employees and 12,000 synthetic attendance logs')
    parser.add_argument('--payroll-port', type=int, default=8878)
    parser.add_argument('--app-port', type=int, default=8890)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if not (root / 'frontend' / 'dist' / 'index.html').exists():
        parser.error('Build the desktop frontend first: cd frontend && npm run build')
    server = create_server(args.payroll_port)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    app = None
    try:
        lane = server.demo.retry_lane
        lane.db.update_api_config(pull_interval_minutes=0, push_interval_minutes=0)
        lane.sync()
        if args.large:
            print(seed_large_queue(lane.db), flush=True)
        lane.mapping_fixed = True
        print(f'Mini Payroll: {server.demo.base_url}/retry/', flush=True)
        print(f'Isolated database: {lane.db.db_path}', flush=True)

        import main as desktop
        # These overrides live only in this test process. The shipping app and
        # its default database/configuration paths are unchanged.
        desktop.Database = lambda: lane.db
        desktop.DEV_MODE = False
        desktop.HTTP_PORT = args.app_port

        class TestApp(desktop.IntegrationApp):
            def create_web_view(self):
                super().create_web_view()
                self.main_window.setWindowTitle('Biometric Integration — TEST / Mini Payroll')
                self.view.loadFinished.connect(self.ready)
                self.main_window.raise_()
                self.main_window.activateWindow()

            def ready(self, loaded):
                if loaded:
                    self.view.page().runJavaScript("window.dispatchEvent(new Event('openRetryQueue'))")
                    print('DESKTOP_READY: real Vue app and QWebChannel loaded', flush=True)

        app = TestApp()
        return app.run()
    finally:
        if app is not None and hasattr(app, 'scheduler'):
            app.scheduler.stop()
        server.demo.close()
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    sys.exit(main())
