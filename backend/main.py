"""
Attendance Sync - Main Application
Desktop application for syncing attendance data between ZKTeco devices and cloud payroll
"""

import sys
import os
import platform
import traceback
from datetime import datetime

# =============================================================================
# EARLY LOGGING SETUP - Before any other imports that might fail
# =============================================================================

# Determine if running as frozen executable (PyInstaller bundle)
IS_FROZEN = getattr(sys, 'frozen', False)

# Configure log file path
import tempfile
if IS_FROZEN:
    LOG_DIR = os.path.join(tempfile.gettempdir(), 'zkteco_integration', 'system_logs')
else:
    LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'system_logs')

os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, datetime.now().strftime('%Y%m%d') + '.log')

def early_log(message):
    """Write to log file before logging module is configured"""
    try:
        with open(LOG_FILE, 'a') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} - EARLY - {message}\n")
    except:
        pass

# Create log file and write startup marker
early_log("=" * 60)
early_log("APPLICATION STARTING")
early_log(f"Python: {sys.version}")
early_log(f"Platform: {platform.system()} {platform.release()}")
early_log(f"Frozen: {IS_FROZEN}")
early_log(f"Executable: {sys.executable}")
early_log("=" * 60)

# =============================================================================
# NATIVE SPLASH SCREEN - Show before heavy imports using Tkinter
# =============================================================================

_tk_root = None
_tk_splash = None

def show_native_splash():
    """Show a native splash window using Tkinter before PyQt6 loads"""
    global _tk_root, _tk_splash
    if IS_FROZEN:
        try:
            import tkinter as tk

            _tk_root = tk.Tk()
            _tk_root.title("Attendance Sync")

            # Remove window decorations
            _tk_root.overrideredirect(True)

            # Window size
            width, height = 400, 200

            # Center on screen
            screen_width = _tk_root.winfo_screenwidth()
            screen_height = _tk_root.winfo_screenheight()
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
            _tk_root.geometry(f"{width}x{height}+{x}+{y}")

            # Set background color
            _tk_root.configure(bg="#1e40af")

            # App name
            title_label = tk.Label(
                _tk_root,
                text="Attendance",
                font=("Arial", 28, "bold"),
                fg="white",
                bg="#1e40af"
            )
            title_label.pack(pady=(40, 0))

            # Subtitle
            subtitle_label = tk.Label(
                _tk_root,
                text="Sync",
                font=("Arial", 14),
                fg="white",
                bg="#1e40af"
            )
            subtitle_label.pack(pady=(5, 0))

            # Loading message
            loading_label = tk.Label(
                _tk_root,
                text="Loading, please wait...",
                font=("Arial", 11),
                fg="#93c5fd",
                bg="#1e40af"
            )
            loading_label.pack(pady=(30, 0))

            # Version
            version_label = tk.Label(
                _tk_root,
                text="Version 1.0.0",
                font=("Arial", 9),
                fg="#60a5fa",
                bg="#1e40af"
            )
            version_label.pack(pady=(20, 0))

            # Bring to front
            _tk_root.lift()
            _tk_root.attributes('-topmost', True)
            _tk_root.update()

            early_log("Tkinter splash screen shown")
        except Exception as e:
            early_log(f"Tkinter splash error: {e}")

def close_native_splash():
    """Close Tkinter splash"""
    global _tk_root, _tk_splash
    try:
        if _tk_root:
            _tk_root.destroy()
            _tk_root = None
            early_log("Tkinter splash closed")
    except Exception as e:
        early_log(f"Error closing Tkinter splash: {e}")

# Show native splash immediately
show_native_splash()

# =============================================================================
# IMPORTS - Wrapped in try-catch to log any import errors
# =============================================================================

try:
    early_log("Importing standard libraries...")
    import logging
    from pathlib import Path
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    import threading

    early_log("Importing PyQt6 (this may take a while on first run)...")
    from PyQt6.QtWidgets import QApplication, QSplashScreen, QLabel, QVBoxLayout, QWidget, QMainWindow, QMenuBar, QMenu
    from PyQt6.QtCore import QUrl, Qt, QTimer
    from PyQt6.QtGui import QPixmap, QFont, QColor, QPainter, QAction, QKeySequence
    early_log("PyQt6 base imported")

    from PyQt6.QtWebEngineWidgets import QWebEngineView
    early_log("QtWebEngineWidgets imported")

    from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile
    early_log("QtWebEngineCore imported")

    from PyQt6.QtWebChannel import QWebChannel
    early_log("QtWebChannel imported")

    early_log("Importing local modules...")
    from database import Database
    from bridge import Bridge
    from services.pull_service import PullService
    from services.push_service import PushService
    from services.scheduler import SyncScheduler

    early_log("All imports successful!")

except Exception as e:
    early_log(f"IMPORT ERROR: {e}")
    early_log(traceback.format_exc())
    close_native_splash()
    sys.exit(1)

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

logging.basicConfig(
    level=logging.DEBUG if not IS_FROZEN else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Dev mode: True for development, False when frozen (packaged)
DEV_MODE = not IS_FROZEN
HTTP_PORT = 8765


def get_frontend_path():
    """Get the path to frontend/dist folder, works for both dev and packaged"""
    if IS_FROZEN:
        # PyInstaller bundle: files are in sys._MEIPASS
        base_path = Path(sys._MEIPASS)
        frontend_dir = base_path / 'frontend' / 'dist'
    else:
        # Development: relative to this file
        frontend_dir = Path(__file__).parent.parent / 'frontend' / 'dist'

    early_log(f"Frontend path: {frontend_dir}")
    early_log(f"Frontend exists: {frontend_dir.exists()}")

    if frontend_dir.exists():
        early_log(f"Frontend contents: {list(frontend_dir.iterdir())[:10]}")

    return frontend_dir


def create_splash_pixmap():
    """Create a splash screen pixmap programmatically"""
    width, height = 400, 250
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor("#1e40af"))  # Primary blue color

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Draw app name
    painter.setPen(QColor("white"))
    font = QFont("Arial", 24, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect().adjusted(0, 50, 0, 0), Qt.AlignmentFlag.AlignHCenter, "Attendance")

    # Draw subtitle
    font = QFont("Arial", 14)
    painter.setFont(font)
    painter.drawText(pixmap.rect().adjusted(0, 90, 0, 0), Qt.AlignmentFlag.AlignHCenter, "Sync")

    # Draw loading message
    font = QFont("Arial", 11)
    painter.setFont(font)
    painter.setPen(QColor("#93c5fd"))  # Light blue
    painter.drawText(pixmap.rect().adjusted(0, 160, 0, 0), Qt.AlignmentFlag.AlignHCenter, "Loading, please wait...")

    # Draw version
    font = QFont("Arial", 9)
    painter.setFont(font)
    painter.setPen(QColor("#60a5fa"))
    painter.drawText(pixmap.rect().adjusted(0, 200, 0, 0), Qt.AlignmentFlag.AlignHCenter, "Version 1.0.0")

    painter.end()
    return pixmap


class LocalHTTPRequestHandler(SimpleHTTPRequestHandler):
    """Custom HTTP request handler for serving frontend files"""

    def __init__(self, *args, **kwargs):
        # Serve from frontend/dist directory
        frontend_dir = get_frontend_path()
        super().__init__(*args, directory=str(frontend_dir), **kwargs)

    def log_message(self, format, *args):
        """Override to use logger instead of stdout"""
        logger.debug(f"HTTP: {format % args}")

    def end_headers(self):
        """Add CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()


class IntegrationApp:
    """Main application class"""

    def __init__(self):
        logger.info("Initializing Attendance Sync")

        # Initialize Qt Application FIRST
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Attendance Sync")
        self.app.setOrganizationName("The Abba")

        # Close Tkinter splash and show Qt splash
        close_native_splash()

        self.splash = QSplashScreen(create_splash_pixmap())
        self.splash.show()
        self.app.processEvents()  # Force the splash to display

        logger.info("Qt splash screen displayed")

        # Use QTimer to defer heavy initialization
        # This allows the splash screen to show while loading
        QTimer.singleShot(100, self.initialize_app)

    def initialize_app(self):
        """Initialize the app components (called after splash is shown)"""
        try:
            self.splash.showMessage("Initializing database...",
                Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
                QColor("#93c5fd"))
            self.app.processEvents()

            # Initialize database
            self.database = Database()

            self.splash.showMessage("Starting services...",
                Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
                QColor("#93c5fd"))
            self.app.processEvents()

            # Initialize services
            self.pull_service = PullService(self.database)
            self.push_service = PushService(self.database)

            # Initialize bridge
            self.bridge = Bridge(self.database, self.pull_service, self.push_service)

            # Initialize scheduler
            self.scheduler = SyncScheduler(self.pull_service, self.push_service, self.database)

            # Connect scheduler to bridge
            self.bridge.set_scheduler(self.scheduler)

            self.splash.showMessage("Starting web engine...",
                Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
                QColor("#93c5fd"))
            self.app.processEvents()

            # Start HTTP server if not in dev mode
            if not DEV_MODE:
                self.start_http_server()

            # Create web view
            self.create_web_view()

            logger.info("Application initialized successfully")

            # Close splash and show main window
            self.splash.finish(self.main_window)

            # Start scheduler
            self.scheduler.start()

        except Exception as e:
            logger.error(f"Initialization error: {e}", exc_info=True)
            self.splash.close()
            raise

    def start_http_server(self):
        """Start local HTTP server for serving frontend files"""
        def run_server():
            try:
                server = HTTPServer(('localhost', HTTP_PORT), LocalHTTPRequestHandler)
                logger.info(f"HTTP server started on http://localhost:{HTTP_PORT}")
                server.serve_forever()
            except Exception as e:
                logger.error(f"HTTP server error: {e}")

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

    def create_web_view(self):
        """Create and configure the web view with menu bar"""
        # Create main window
        self.main_window = QMainWindow()
        self.main_window.setWindowTitle("Attendance Sync")

        # Create web view
        self.view = QWebEngineView()

        # Configure web engine settings
        settings = self.view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)

        # Enable developer tools in dev mode
        if DEV_MODE:
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)

        # Set up QWebChannel for Python-JS communication
        self.channel = QWebChannel()
        self.channel.registerObject('bridge', self.bridge)
        self.view.page().setWebChannel(self.channel)

        # Set web view as central widget
        self.main_window.setCentralWidget(self.view)

        # Enable downloads
        profile = QWebEngineProfile.defaultProfile()
        profile.downloadRequested.connect(self.handle_download)

        # Create menu bar
        self.create_menu_bar()

        # Load the frontend
        if DEV_MODE:
            # In dev mode, load from Vite dev server
            url = "http://localhost:5173"
            logger.info(f"Loading from Vite dev server: {url}")
        else:
            # In production, load from local HTTP server
            url = f"http://localhost:{HTTP_PORT}"
            logger.info(f"Loading from local HTTP server: {url}")

        self.view.load(QUrl(url))

        # Window configuration
        self.main_window.resize(1400, 900)

        # Show maximized
        self.main_window.showMaximized()

    def create_menu_bar(self):
        """Create the application menu bar"""
        menubar = self.main_window.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        reload_action = QAction("Reload", self.main_window)
        reload_action.setShortcut(QKeySequence("Ctrl+R"))
        reload_action.triggered.connect(self.view.reload)
        file_menu.addAction(reload_action)

        file_menu.addSeparator()

        quit_action = QAction("Quit", self.main_window)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.app.quit)
        file_menu.addAction(quit_action)

        # View menu
        view_menu = menubar.addMenu("View")

        # Developer Tools (dev mode only)
        if DEV_MODE:
            devtools_action = QAction("Developer Tools", self.main_window)
            devtools_action.setShortcut(QKeySequence("F12"))
            devtools_action.triggered.connect(self.open_devtools)
            view_menu.addAction(devtools_action)

        zoom_in_action = QAction("Zoom In", self.main_window)
        zoom_in_action.setShortcut(QKeySequence("Ctrl++"))
        zoom_in_action.triggered.connect(lambda: self.view.setZoomFactor(self.view.zoomFactor() + 0.1))
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom Out", self.main_window)
        zoom_out_action.setShortcut(QKeySequence("Ctrl+-"))
        zoom_out_action.triggered.connect(lambda: self.view.setZoomFactor(self.view.zoomFactor() - 0.1))
        view_menu.addAction(zoom_out_action)

        reset_zoom_action = QAction("Reset Zoom", self.main_window)
        reset_zoom_action.setShortcut(QKeySequence("Ctrl+0"))
        reset_zoom_action.triggered.connect(lambda: self.view.setZoomFactor(1.0))
        view_menu.addAction(reset_zoom_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self.main_window)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def handle_download(self, download):
        """Handle file downloads from the web view"""
        from PyQt6.QtWidgets import QFileDialog

        # Get suggested filename
        suggested_name = download.downloadFileName()
        logger.info(f"Download requested: {suggested_name}")

        # Ask user where to save
        save_path, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "Save File",
            suggested_name,
            "All Files (*)"
        )

        if save_path:
            download.setDownloadFileName(os.path.basename(save_path))
            download.setDownloadDirectory(os.path.dirname(save_path))
            download.accept()
            logger.info(f"Download accepted: {save_path}")
        else:
            download.cancel()
            logger.info("Download cancelled by user")

    def open_devtools(self):
        """Open developer tools in a new window"""
        if not hasattr(self, 'devtools_view'):
            self.devtools_view = QWebEngineView()
            self.devtools_view.setWindowTitle("Developer Tools")
            self.devtools_view.resize(1200, 800)
        self.view.page().setDevToolsPage(self.devtools_view.page())
        self.devtools_view.show()
        logger.info("Developer tools opened")

    def show_about(self):
        """Show about dialog"""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.about(
            self.main_window,
            "About Attendance Sync",
            "Attendance Sync v1.0.0\n\n"
            "Sync attendance data from ZKTeco devices\n"
            "to cloud payroll systems.\n\n"
            "© 2025 The Abba. All rights reserved."
        )

    def run(self):
        """Run the application"""
        logger.info("Starting application event loop")
        return self.app.exec()


def main():
    """Application entry point"""
    try:
        logger.info("=" * 80)
        logger.info("Attendance Sync Starting")
        logger.info(f"Python Version: {sys.version}")
        logger.info(f"Platform: {platform.system()} {platform.release()}")
        logger.info(f"Frozen (packaged): {IS_FROZEN}")
        logger.info(f"Development Mode: {DEV_MODE}")
        logger.info(f"Log File: {LOG_FILE}")
        logger.info("=" * 80)

        app = IntegrationApp()
        sys.exit(app.run())

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
