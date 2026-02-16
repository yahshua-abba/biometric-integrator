# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Biometric Integration** is a PyQt6 desktop app that pulls attendance data from ZKTeco biometric devices (via PyZk) and pushes it to YAHSHUA Cloud Payroll (via REST API). The frontend is Vue.js 3 + TailwindCSS rendered inside a QWebEngineView, communicating with the Python backend through QWebChannel.

## Common Commands

### Setup
```bash
# Backend
cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# Frontend
cd frontend && npm install
```

### Development (requires two terminals)
```bash
# Terminal 1 - Frontend dev server
cd frontend && npm run dev          # http://localhost:5173

# Terminal 2 - Backend (activate venv first)
cd backend && source venv/bin/activate && python main.py
```

### Build Frontend for Production
```bash
cd frontend && npm run build        # Output: frontend/dist/
```

### Testing Tools
```bash
python backend/mock_server.py       # Mock YAHSHUA API server
python backend/diagnose_device.py   # ZKTeco device diagnostics
```

## Architecture

```
PyQt6 Window → QWebEngineView (Chromium)
                    ↕ QWebChannel
              Python Backend (bridge.py)
              ├── database.py (SQLite, auto-migrations)
              ├── services/pull_service.py → ZKTeco devices (TCP 4370)
              ├── services/push_service.py → YAHSHUA API (HTTPS)
              ├── services/update_service.py → GitHub Releases API
              └── services/scheduler.py (background pull/push/cleanup)
```

### Startup Sequence
1. Tkinter splash screen (fast native appearance)
2. PyQt6 initializes, shows Qt splash
3. Local HTTP server on port 8765 (production) or Vite dev server at localhost:5173 (development)
4. QWebEngineView loads frontend → QWebChannel bridge connects → Scheduler starts

### Key Communication Pattern
Frontend calls Python methods via `bridge.js` → QWebChannel → `bridge.py` (PyQt slots). All bridge methods return JSON strings. Python-to-JS signals: `syncStatusUpdated`, `syncProgressUpdated`, `syncCompleted`.

```javascript
// Frontend pattern
import bridge from '@/services/bridge'
await bridge.whenReady()
const stats = await bridge.getTimesheetStats()
```

### Production vs Development
- **Production:** `IS_FROZEN=True`, serves `frontend/dist/` via local HTTP server on port 8765
- **Development:** Loads from Vite dev server, F12 opens DevTools

## Database

**Location:** `backend/database.py` — SQLite with auto-migrations (new columns/tables added on startup).

### Key Tables
- **`api_config`** — Singleton (CHECK id=1). Push URL, credentials, sync intervals.
- **`device`** — Multi-device support. IP, port, comm_key (password), branch_id. Soft deletes.
- **`employee`** — From ZKTeco devices. `backend_id` = device user ID. Soft deletes.
- **`timesheet`** — Attendance records. `sync_id` format: `ZK_{device_id}_{user_id}_{timestamp}`. `synced_at` NULL = pending push.
- **`sync_logs`** — Operation history. Types: pull/push/config/other.

### Critical Constraints
- Timesheet `sync_id` ensures deduplication across devices and pulls
- `log_type` is `'in'` or `'out'` (CHECK constraint) — mapped from ZKTeco punch types (0,3,4→in; 1,2,5→out)
- Soft deletes: always filter with `WHERE deleted_at IS NULL`
- Legacy `device_ip`/`device_port` in `api_config` are deprecated; auto-migrated to `device` table on first run

## ZKTeco Device Communication

**`backend/services/pull_service.py`** — Uses PyZk library.

```python
self.zk = ZK(ip, port=port, timeout=30, password=comm_key or 0)
```

Punch type mapping: 0=Check-In, 1=Check-Out, 2=Break-Out, 3=Break-In, 4=OT-In, 5=OT-Out → mapped to `in`/`out`.

## YAHSHUA Payroll API

**`backend/services/push_service.py`** — Token-based auth, batch processing (50 records/request), auto re-auth on 401.

- Auth: `POST {base_url}/api/api-auth/?username={}&password={}`
- Push: `POST {base_url}/api/sync-time-in-out/` with `Authorization: Token {token}`
- Response tracks individual record success/failure with error codes

## Version Management

Version is determined automatically — no manual version bumps needed in code:

- **Production (CI builds):** GitHub Actions writes a `VERSION` file from the git tag (`${GITHUB_REF_NAME#v}`)
- **Development:** `backend/version.py` reads the latest git tag via `git describe --tags --abbrev=0`
- **Frontend:** `App.vue` has a hardcoded fallback in `appVersion` ref but fetches the real version from the backend on mount

The only place that needs a manual version update is the frontend fallback in `frontend/src/App.vue` (`appVersion` ref).

## Release Process

### Creating a Release
```bash
git tag v1.0.X
git push origin v1.0.X
```

GitHub Actions (`build-release.yml`) triggers on `v*.*.*` tags and:
1. Builds macOS DMG (runner: `macos-15-intel`) and Windows ZIP (runner: `windows-latest`)
2. Uploads both to GitHub Releases and S3 (`s3://yp-files/biometrics-integration/`)

### IMPORTANT: GitHub Release Notes

**After the CI build completes, you MUST update the GitHub release with proper user-facing release notes.** The CI uses `generate_release_notes: true` which only produces a git changelog link — not useful for end users.

Update the release body using:
```bash
gh release edit v1.0.X --notes "$(cat <<'EOF'
## What's New
- [Feature descriptions written for end users/clients]

## Improvements
- [Bug fixes and enhancements]
EOF
)"
```

The release notes are displayed in the app's **Updates** page (via `UpdatesView.vue` → `update_service.get_all_releases()` → GitHub API). Users see the `body` field from GitHub releases directly in the app, so notes must be clear, non-technical, and written for the client's consumption. Only releases from v1.0.15 onwards are shown.

## Scheduler

| Schedule | Config Field | Default |
|----------|-------------|---------|
| Pull from devices | `pull_interval_minutes` | 30 min (0=disabled) |
| Push to payroll | `push_interval_minutes` | 15 min (0=disabled) |
| Cleanup old records | Fixed daily 02:00 AM | Records >60 days |

## Bridge API Reference

All methods in `backend/bridge.py` are exposed as PyQt slots. Key groups:

- **Timesheet:** `getTimesheetStats`, `getAllTimesheets`, `getUnsyncedTimesheets`, `retryFailedTimesheet`, `clearTimesheets`
- **Sync:** `startPullSync`, `startPullSyncWithDevice` (device_id=-1 for all), `startPushSync`, `getSyncLogs`
- **Config:** `getApiConfig` (credentials masked as '***'), `updateApiConfig`, `loginPush`, `logoutPush`
- **Devices:** `getDevices`, `addDevice`, `updateDevice`, `deleteDevice`, `testDeviceConnection`
- **Updates:** `checkForUpdates`, `getAllReleases`, `downloadUpdate`, `openDownloadedUpdate`
- **Utility:** `getAppInfo`, `triggerCleanup`, `getSystemLogFiles`, `getSystemLogContent`

## Frontend Structure

- **App.vue** — Sidebar navigation + version display. Views: Dashboard, Timesheets, Configuration, Logs, Updates, Help & FAQ
- **DashboardView.vue** — Stats cards, pull (with device selector + date range), push (with progress modal)
- **TimesheetView.vue** — Paginated table with filters (search, date, device, status)
- **ConfigView.vue** — YAHSHUA login, device CRUD, system log viewer
- **UpdatesView.vue** — Version checker, download/install, release history from GitHub
- **HelpView.vue** — Setup guides, troubleshooting, FAQ, compatible devices

## GitHub Repository

- **Org:** `ysc-payroll` (API URLs in update_service.py)
- **Repo remote:** `yahshua-abba/biometric-integrator`
- **Main branch:** `main`
