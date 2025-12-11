# Biometric Integration - Developer Documentation

> **For AI Assistants (Claude):** This document provides comprehensive context for understanding and working with this codebase. Read this first before making changes.

## Project Overview

**Biometric Integration** is a desktop application that bridges two systems:
1. **ZKTeco Attendance Devices** - Source of employee attendance/timesheet data (via PyZk library)
2. **Cloud Payroll Systems** - Destination for syncing timesheet data

The app runs on the client's local machine, pulls data from ZKTeco devices on the network, and pushes it to the cloud payroll system.

## Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.10+ with PyQt6 |
| Frontend | Vue.js 3 + Vite + TailwindCSS |
| Database | SQLite (local) |
| Communication | QWebChannel (Python ↔ JavaScript bridge) |
| Device | PyZk (ZKTeco SDK) |
| Packaging | PyInstaller (creates standalone executables) |
| CI/CD | GitHub Actions |

## Project Structure

```
zkteco-integration/
├── backend/                      # Python backend
│   ├── main.py                   # Application entry point
│   ├── bridge.py                 # QWebChannel bridge (exposes Python methods to JS)
│   ├── database.py               # SQLite database manager
│   ├── services/
│   │   ├── pull_service.py       # Fetch data from ZKTeco device
│   │   ├── push_service.py       # Push data to YAHSHUA API
│   │   └── scheduler.py          # Background sync scheduler
│   ├── sanbeda-integration.spec  # PyInstaller config (macOS)
│   ├── sanbeda-integration-windows.spec  # PyInstaller config (Windows)
│   ├── create_dmg.sh             # macOS DMG creation script
│   └── requirements.txt          # Python dependencies
│
├── frontend/                     # Vue.js frontend
│   ├── src/
│   │   ├── App.vue               # Main app with sidebar navigation
│   │   ├── components/
│   │   │   ├── DashboardView.vue    # Stats + manual sync buttons
│   │   │   ├── TimesheetView.vue    # Timesheet data table
│   │   │   ├── ConfigView.vue       # Device/API configuration
│   │   │   ├── LogsView.vue         # Sync activity logs
│   │   │   ├── SyncProgressModal.vue # Push sync progress indicator
│   │   │   └── ToastNotification.vue # Toast messages
│   │   ├── services/
│   │   │   └── bridge.js            # QWebChannel client wrapper
│   │   └── composables/
│   │       └── useToast.js          # Toast notification composable
│   ├── package.json
│   └── vite.config.js
│
├── icons/                        # App icons
│   ├── icon.icns                 # macOS icon
│   ├── icon_1024x1024.png        # Source PNG
│   └── create_ico.py             # Generates Windows ICO
│
└── .github/workflows/
    └── build-release.yml         # GitHub Actions build workflow
```

---

## Architecture

### How the App Works

```
┌─────────────────────────────────────────────────────────────┐
│                     Desktop Application                      │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    PyQt6 Window                         ││
│  │  ┌─────────────────────────────────────────────────────┐││
│  │  │              QWebEngineView (Chromium)              │││
│  │  │  ┌───────────────────────────────────────────────┐  │││
│  │  │  │            Vue.js Frontend (HTML/JS/CSS)      │  │││
│  │  │  └───────────────────────────────────────────────┘  │││
│  │  │                        ↕ QWebChannel                │││
│  │  └─────────────────────────────────────────────────────┘││
│  │                           ↕                              ││
│  │  ┌─────────────────────────────────────────────────────┐││
│  │  │              Python Backend (Bridge)                │││
│  │  │         Database │ PullService │ PushService        │││
│  │  └─────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
          ↓                                        ↓
┌──────────────────────┐              ┌──────────────────────┐
│   ZKTeco Device      │              │   YAHSHUA Cloud      │
│   (TCP/IP Port 4370) │              │   Payroll API        │
│                      │              │   (HTTPS, Bearer)    │
└──────────────────────┘              └──────────────────────┘
```

---

## ZKTeco Device Communication

### Pull Service (`backend/services/pull_service.py`)

Uses PyZk library to communicate with ZKTeco devices:

```python
from zk import ZK

class PullService:
    def connect(self):
        ip, port, _ = self.get_device_config()
        self.zk = ZK(ip, port=port, timeout=10)
        self.conn = self.zk.connect()
        return self.conn

    def pull_data(self, date_from, date_to, progress_callback=None):
        conn = self.connect()
        attendance = conn.get_attendance()  # All attendance logs
        users = conn.get_users()  # All users/employees
        # Filter by date range and save to database
```

### Punch Types
- 0 = Check-In
- 1 = Check-Out
- 2 = Break-Out
- 3 = Break-In
- 4 = OT-In
- 5 = OT-Out

The service maps punch types 0, 3, 4 as 'in' and others as 'out'.

---

## YAHSHUA Authentication (Push)

**Location:** `backend/services/push_service.py`

YAHSHUA uses **standard Bearer token** authentication:

```
POST /api/auth/login
Body: { "email": "user@example.com", "password": "..." }
Response: { "token": "eyJ...", "user_logged": "John Doe", ... }
```

**Token Storage:** Stored in `api_config.push_token` in SQLite database.

---

## Database Schema

**Location:** `backend/database.py`

### Tables

#### `api_config` (singleton - always 1 row)
```sql
- device_ip           -- ZKTeco device IP address
- device_port         -- ZKTeco device port (default 4370)
- push_url            -- YAHSHUA API URL
- push_username       -- YAHSHUA email
- push_password       -- YAHSHUA password
- push_token          -- YAHSHUA Bearer token
- push_user_logged    -- YAHSHUA user display name
- pull_interval_minutes  -- Auto-pull interval (0 = disabled)
- push_interval_minutes  -- Auto-push interval (0 = disabled)
```

#### `timesheet`
```sql
- id                 -- Primary key
- sync_id            -- Unique ID (ZK_{user_id}_{timestamp})
- employee_id        -- FK to employee table
- log_type           -- 'in' or 'out'
- date               -- Date (YYYY-MM-DD)
- time               -- Time (HH:MM:SS)
- backend_timesheet_id -- YAHSHUA ID (set when pushed)
- synced_at          -- When pushed to YAHSHUA (NULL = pending)
- sync_error_message -- Error if push failed
```

#### `employee`
```sql
- id                 -- Primary key
- backend_id         -- User ID from ZKTeco device
- name               -- User name from device
- employee_code      -- Same as backend_id (for matching)
```

---

## Development Setup

### Prerequisites
- Python 3.10+
- Node.js 20+
- macOS or Windows
- ZKTeco device on the network (for testing)

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend Setup
```bash
cd frontend
npm install
```

### Running in Development

**Terminal 1 - Frontend (Vite dev server):**
```bash
cd frontend
npm run dev
# Runs on http://localhost:5173
```

**Terminal 2 - Backend:**
```bash
cd backend
source venv/bin/activate
python main.py
# Opens PyQt window pointing to Vite dev server
```

---

## Version Management

**Update version in these files before releasing:**

| File | Location |
|------|----------|
| `backend/bridge.py` | `getAppInfo()` - version field |
| `backend/main.py` | Tkinter splash version label |
| `backend/main.py` | Qt splash version label |
| `frontend/src/App.vue` | appVersion ref (auto-fetched from backend) |

---

## Configuration

### Device Configuration
1. Enter the ZKTeco device IP address
2. Enter the port (default 4370)
3. Click "Test Connection" to verify

### Push Configuration
1. Enter YAHSHUA Payroll credentials
2. Click "Login" to authenticate
3. Set push interval for automatic sync

---

## Setup

1. Install the Integration App (wait 1-2 minutes for first initialization)
2. Go to Configuration
3. Setup Device IP/Port and YAHSHUA login
4. Click "Pull" button in Dashboard or wait for auto download/upload
