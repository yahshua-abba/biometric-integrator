# Biometric Integration - Developer Documentation

> **For AI Assistants (Claude):** This document provides comprehensive context for understanding and working with this codebase. Read this first before making changes.

## Project Overview

**Biometric Integration** is a desktop application that bridges two systems:
1. **ZKTeco Attendance Devices** - Source of employee attendance/timesheet data (via PyZk library)
2. **Cloud Payroll Systems** - Destination for syncing timesheet data (YAHSHUA Payroll)

The app runs on the client's local machine, pulls data from one or more ZKTeco devices on the network, and pushes it to the cloud payroll system. It supports **multi-device management** with per-device configuration including comm key (password) and branch ID.

## Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.10+ with PyQt6 |
| Frontend | Vue.js 3 + Vite + TailwindCSS |
| Database | SQLite (local) |
| Communication | QWebChannel (Python <-> JavaScript bridge) |
| Device | PyZk >= 0.9 (ZKTeco SDK) |
| Packaging | PyInstaller (creates standalone executables) |
| CI/CD | GitHub Actions |

## Project Structure

```
integrator_sanbeda_taytay/
├── backend/
│   ├── main.py                           # App entry point (splash screen, PyQt6 window)
│   ├── bridge.py                         # QWebChannel bridge (Python methods exposed to JS)
│   ├── database.py                       # SQLite database manager with auto-migrations
│   ├── services/
│   │   ├── __init__.py
│   │   ├── pull_service.py              # ZKTeco device communication (multi-device)
│   │   ├── push_service.py              # YAHSHUA Payroll API integration
│   │   └── scheduler.py                 # Background sync scheduler
│   ├── mock_server.py                   # Mock YAHSHUA server for testing
│   ├── diagnose_device.py              # ZKTeco device diagnostic tool
│   ├── sanbeda-integration.spec         # PyInstaller config (macOS)
│   ├── sanbeda-integration-windows.spec # PyInstaller config (Windows)
│   ├── create_dmg.sh                    # macOS DMG creation script
│   └── requirements.txt                 # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── main.js                      # Vue app entry point
│   │   ├── style.css                    # Global styles
│   │   ├── App.vue                      # Main app with sidebar navigation
│   │   ├── components/
│   │   │   ├── DashboardView.vue        # Stats + manual sync buttons + device selector
│   │   │   ├── TimesheetView.vue        # Timesheet data table with filters
│   │   │   ├── ConfigView.vue           # Device/API config + system log viewer
│   │   │   ├── LogsView.vue             # Sync activity logs + cleanup trigger
│   │   │   ├── SyncProgressModal.vue    # Push sync progress indicator
│   │   │   └── ToastNotification.vue    # Toast messages
│   │   ├── services/
│   │   │   └── bridge.js               # QWebChannel client wrapper
│   │   └── composables/
│   │       └── useToast.js              # Toast notification composable
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
│
├── icons/
│   ├── icon.icns                        # macOS icon
│   ├── icon_1024x1024.png              # Source PNG
│   └── create_ico.py                    # Generates Windows ICO
│
├── .github/workflows/
│   └── build-release.yml                # GitHub Actions build workflow
│
└── CLAUDE.md                            # This file
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
│  │  │    Database │ PullService │ PushService │ Scheduler │││
│  │  └─────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
     ↓                    ↓                         ↓
┌──────────┐   ┌──────────┐          ┌──────────────────────┐
│ ZKTeco   │   │ ZKTeco   │          │   YAHSHUA Cloud      │
│ Device 1 │   │ Device N │          │   Payroll API        │
│ TCP 4370 │   │ TCP 4370 │          │   (HTTPS, Token)     │
└──────────┘   └──────────┘          └──────────────────────┘
```

### Startup Sequence
1. Native Tkinter splash screen shows immediately (fast appearance)
2. PyQt6 initializes and shows a Qt splash screen
3. Local HTTP server starts on port 8765 (production) or Vite dev server (dev)
4. QWebEngineView loads the frontend
5. QWebChannel bridge connects Python backend to JavaScript frontend
6. Scheduler starts background sync tasks

---

## Database Schema

**Location:** `backend/database.py`

The database uses auto-migrations - new columns/tables are added automatically on startup.

### Tables

#### `api_config` (singleton - always 1 row, CHECK id=1)
```sql
device_ip              -- Legacy device IP (deprecated, use device table)
device_port            -- Legacy device port (deprecated, default 4370)
push_url               -- YAHSHUA API base URL
push_auth_type         -- Authentication type
push_credentials       -- Generic credentials field
push_username          -- YAHSHUA email/username
push_password          -- YAHSHUA password
push_token             -- Bearer token from YAHSHUA
push_token_created_at  -- Token creation timestamp
push_user_logged       -- YAHSHUA user display name
pull_interval_minutes  -- Auto-pull interval (0 = disabled, default 30)
push_interval_minutes  -- Auto-push interval (0 = disabled, default 15)
last_pull_at           -- Last pull timestamp (legacy)
last_push_at           -- Last push timestamp
updated_at             -- Last config update
```

#### `device` (multi-device support)
```sql
id            -- Primary key (autoincrement)
name          -- Device friendly name
ip            -- Device IP address
port          -- Device port (default 4370)
comm_key      -- Device communication password (integer, 0 = none)
branch_id     -- YAHSHUA branch identifier for this device
enabled       -- Enable/disable device (default 1)
last_pull_at  -- Last successful pull timestamp
created_at    -- Creation timestamp
updated_at    -- Last update timestamp
deleted_at    -- Soft delete timestamp (NULL = active)
```
**Indexes:** `idx_device_enabled`, `idx_device_deleted_at`, `idx_device_unique_ip_active`

#### `employee`
```sql
id              -- Primary key (autoincrement)
backend_id      -- User ID from ZKTeco device (unique)
name            -- Employee name from device
employee_code   -- Employee code (supports alphanumeric)
employee_number -- Employee number
created_at      -- Creation timestamp
deleted_at      -- Soft delete timestamp
```
**Indexes:** `idx_employee_backend_id`, `idx_employee_code`, `idx_employee_deleted_at`

#### `timesheet`
```sql
id                    -- Primary key (autoincrement)
sync_id               -- Unique ID format: ZK_{device_id}_{user_id}_{timestamp}
employee_id           -- FK to employee.id
log_type              -- 'in' or 'out' (CHECK constraint)
date                  -- Date (YYYY-MM-DD)
time                  -- Time (HH:MM:SS)
photo_path            -- Path to photo (if device supports)
is_synced             -- Legacy sync indicator (default 0)
status                -- Record status (default 'success')
error_message         -- Generic error message
created_at            -- Creation timestamp
backend_timesheet_id  -- ID returned from YAHSHUA after sync
synced_at             -- When pushed to YAHSHUA (NULL = pending)
sync_error_message    -- Error details from YAHSHUA push
device_id             -- FK to device.id (which device this came from)
```
**Indexes:** `idx_timesheet_sync_id`, `idx_timesheet_employee_id`, `idx_timesheet_date`, `idx_timesheet_is_synced`, `idx_timesheet_backend_id`, `idx_timesheet_device_id`

#### `sync_logs` (operation tracking)
```sql
id                 -- Primary key (autoincrement)
sync_type          -- 'pull', 'push', 'config', or 'other' (CHECK constraint)
status             -- 'started', 'success', or 'error' (CHECK constraint)
records_processed  -- Total records handled (default 0)
records_success    -- Successfully processed (default 0)
records_failed     -- Failed records (default 0)
error_message      -- Error details
started_at         -- Operation start time
completed_at       -- Operation completion time
metadata           -- JSON with additional context (device_id, device_name, etc.)
```
**Indexes:** `idx_sync_logs_type`, `idx_sync_logs_status`, `idx_sync_logs_started`

#### `company` (reserved for future multi-tenant)
```sql
id, backend_id, name, created_at
```

#### `users` (reserved for future admin users)
```sql
id (CHECK id=1), email, name, is_active, last_login, created_at
```

---

## ZKTeco Device Communication

### Pull Service (`backend/services/pull_service.py`)

Uses PyZk library to communicate with ZKTeco devices. Supports **multi-device** architecture.

```python
# Connection with comm key (password) support
self.zk = ZK(ip, port=port, timeout=30, password=comm_key or 0)
self.conn = self.zk.connect()
```

### Key Methods
- `connect(device_id=None)` - Connect with optional comm_key password
- `test_connection(device_id=None)` - Test connectivity, returns device info (name, serial, firmware)
- `pull_data(date_from, date_to, device_id, progress_callback)` - Multi-device pull with aggregated stats
- `get_device_users()` - List enrolled users from device
- `clear_device_attendance()` - Clear attendance logs on device

### Punch Type Mapping
| Punch | Type | Maps To |
|-------|------|---------|
| 0 | Check-In | `in` |
| 1 | Check-Out | `out` |
| 2 | Break-Out | `out` |
| 3 | Break-In | `in` |
| 4 | OT-In | `in` |
| 5 | OT-Out | `out` |

### Sync ID Format
`ZK_{device_id}_{user_id}_{timestamp}` - Ensures uniqueness across multiple devices and pulls.

---

## YAHSHUA Payroll API (Push)

**Location:** `backend/services/push_service.py`

### Endpoints

**Authentication:**
```
POST {base_url}/api/api-auth/?username={}&password={}
Response: { "token": "...", "user_logged": "John Doe", "company_name": "..." }
```

**Push Timesheet Data:**
```
POST {base_url}/api/sync-time-in-out/
Authorization: Token {token}
Body:
{
  "from_biometrics": true,
  "from_new_biometrics": true,
  "log_list": [
    {
      "id": local_timesheet_id,
      "employee": employee_code,
      "log_time": "HH:MM",
      "log_type": "IN" or "OUT",
      "sync_id": "ZK_...",
      "date": "YYYY-MM-DD",
      "branch_id": "BRANCH001"  // optional, from device.branch_id
    }
  ]
}
Response: { "logs_successfully_sync": [ids], "logs_not_sync": [{id, reason, error_code}] }
```

### Features
- Batch processing: 50 records per request
- Auto re-authentication on 401 (expired token)
- Individual record error tracking
- Progress callbacks for UI updates
- Optional `branch_id` per device for multi-branch routing

---

## Bridge API (`backend/bridge.py`)

### Signals (Python -> JavaScript)
| Signal | Description |
|--------|-------------|
| `syncStatusUpdated` | JSON with sync status changes |
| `syncProgressUpdated` | JSON with progress (batch, device index, counts) |
| `syncCompleted` | JSON with final results |

### Exposed Methods (PyQt Slots)

**Timesheet:**
- `getTimesheetStats()` -> `{total, synced, pending, errors}`
- `getAllTimesheets(limit=1000, offset=0)` -> Paginated list
- `getUnsyncedTimesheets(limit=100)` -> Unsynced records with employee & branch info
- `retryFailedTimesheet(timesheet_id)` -> Clear error to retry
- `clearTimesheets(date_from, date_to, only_synced=True)` -> Delete records in range

**Employee:**
- `getAllEmployees()` -> List of active employees

**Sync:**
- `startPullSync(date_from, date_to)` -> Pull from all enabled devices
- `startPullSyncWithDevice(date_from, date_to, device_id)` -> Pull from specific device (-1 = all)
- `startPushSync()` -> Push all unsynced records
- `getSyncLogs()` -> Recent 100 sync log entries

**Configuration:**
- `getApiConfig()` -> Current config (credentials masked as '***')
- `updateApiConfig(config_json)` -> Update settings (only provided fields)
- `testConnection(connection_type)` -> Test 'device' or 'push' connection
- `loginPush(username, password)` -> Authenticate with YAHSHUA
- `logoutPush()` -> Clear authentication token

**Device Management:**
- `getDevices()` -> List all active devices
- `addDevice(name, ip, port, comm_key, branch_id)` -> Add device
- `updateDevice(device_id, name, ip, port, comm_key, branch_id, enabled)` -> Update device
- `deleteDevice(device_id)` -> Soft delete device
- `testDeviceConnection(device_id)` -> Test specific device
- `getDeviceUsers()` -> List users from ZKTeco device

**Utility:**
- `getAppInfo()` -> `{name, version, description}`
- `triggerCleanup()` -> Manual cleanup of old records
- `getSystemLogFiles()` -> List available log files
- `getSystemLogContent(filename)` -> Last 500 lines of log file

---

## Scheduler (`backend/services/scheduler.py`)

| Schedule | Interval | Default |
|----------|----------|---------|
| Pull | Every `pull_interval_minutes` | 30 min (0 = disabled) |
| Push | Every `push_interval_minutes` | 15 min (0 = disabled) |
| Cleanup | Daily at 02:00 AM | Deletes records older than 60 days |

Methods: `start()`, `stop()`, `update_schedules()`, `trigger_pull_now()`, `trigger_push_now()`, `trigger_cleanup_now()`

---

## Frontend Components

### App.vue
Sidebar navigation (Dashboard, Timesheets, Config, Logs) + toast notifications + version display.

### DashboardView.vue
- Stats cards: Total, Synced, Pending, Errors
- Pull sync with date range modal and **device selector** (all or specific)
- Push sync with progress modal
- Recent activity feed (last 10 sync logs)

### TimesheetView.vue
- Paginated data table with columns: Date/Time, Employee, Device, Type, Status, Sync ID, Error
- Filters: search, date range, device, status (All/Synced/Pending/Errors)
- Actions: clear records (by date range), retry failed, refresh

### ConfigView.vue
- YAHSHUA login/logout with interval config
- Device management table: Add, Edit, Delete, Test Connection per device
- Device fields: Name, IP, Port, Comm Key (password), Branch ID, Enabled
- System log viewer: file list, view last 500 lines, download

### LogsView.vue
- Sync logs table with type/status filters
- Columns: Type, Status, Records, Started, Duration, Message
- Manual cleanup trigger button

### SyncProgressModal.vue
- Batch progress bar with success/failed counters

---

## Frontend Bridge (`frontend/src/services/bridge.js`)

Wrapper around QWebChannel. All methods return Promises. Key pattern:

```javascript
import bridge from '@/services/bridge'
await bridge.whenReady()
const stats = await bridge.getTimesheetStats()
```

---

## Development Setup

### Prerequisites
- Python 3.10+
- Node.js 20+
- macOS or Windows
- ZKTeco device on the network (for testing, or use `backend/mock_server.py`)

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

### Testing Tools
- `backend/mock_server.py` - Simulates YAHSHUA API for development
- `backend/diagnose_device.py` - Diagnose ZKTeco device connectivity issues

---

## Build & Release

### CI/CD (`build-release.yml`)
Triggered on version tags (`v*.*.*`).

**macOS:** Runner `macos-15-intel` -> PyInstaller -> DMG
**Windows:** Runner `windows-latest` -> PyInstaller -> ZIP

Both uploaded as GitHub Release assets.

### PyInstaller Config
- Bundle ID: `com.theabba.biometric-integration`
- macOS min version: 10.13.0
- Frontend `dist/` files included as data
- Hidden imports: PyQt6, requests, schedule, Crypto modules

---

## Version Management

**Current Version: 1.0.0**

Update version in these files before releasing:

| File | Location |
|------|----------|
| `backend/bridge.py` | `getAppInfo()` - version field |
| `backend/main.py` | Tkinter splash version label |
| `backend/main.py` | Qt splash version label |
| `backend/sanbeda-integration.spec` | Bundle version strings |
| `frontend/src/App.vue` | appVersion ref (auto-fetched from backend) |

---

## Key Implementation Details

### Production vs Development Mode
- **Production:** Local HTTP server on port 8765 serves `frontend/dist/`
- **Development:** Loads from Vite dev server at `localhost:5173`, F12 opens DevTools

### Soft Deletes
Devices and employees use `deleted_at` timestamps instead of hard deletes. Queries filter with `WHERE deleted_at IS NULL`.

### Legacy Device Migration
The `device_ip`/`device_port` fields in `api_config` are deprecated. On first run, if they exist and no device records are present, the database auto-migrates them into the `device` table.

### Error Handling Patterns
- **Database:** Try-catch with rollback, unique constraint for deduplication
- **API:** HTTP status checks, 401 triggers auto re-auth, per-record error tracking
- **Device:** Connection failures logged, timeout=30s, disconnect in finally block
- **Frontend:** Toast notifications + Promise rejection handling

---

## Configuration

### Device Configuration
1. Go to Configuration tab
2. Add a new device with Name, IP, Port
3. Optionally set Comm Key (password) if the device requires it
4. Optionally set Branch ID for YAHSHUA multi-branch routing
5. Click "Test Connection" to verify

### Push Configuration
1. Enter YAHSHUA Payroll URL and credentials
2. Click "Login" to authenticate
3. Set push interval for automatic sync

---

## Setup (End User)

1. Install the Integration App (wait 1-2 minutes for first initialization)
2. Go to Configuration
3. Add ZKTeco device(s) with IP/Port/Comm Key
4. Login to YAHSHUA Payroll
5. Click "Pull" button in Dashboard or configure auto-sync intervals
