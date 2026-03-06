# Biometric Integration

A desktop application that syncs attendance data from ZKTeco biometric devices to cloud payroll systems.

## Features

- **Pull** - Fetch attendance data from ZKTeco devices
- **Push** - Sync timesheet data to cloud payroll
- **Multi-Device** - Support multiple ZKTeco devices on the network
- **Auto Sync** - Configurable automatic sync intervals
- **Offline-First** - Works without internet, syncs when online
- **Activity Logs** - Complete history of all sync operations

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.10+ / PyQt6 |
| Frontend | Vue.js 3 / Vite / TailwindCSS |
| Database | SQLite |
| Device | PyZk (ZKTeco SDK) |
| Packaging | PyInstaller |
| CI/CD | GitHub Actions |

## Installation

### macOS
1. Download `BiometricIntegration-vX.X.X.dmg` from Releases
2. Open DMG and drag to Applications
3. First launch takes 1-2 minutes (one-time initialization)

### Windows
1. Download `BiometricIntegration-vX.X.X-Windows.zip` from Releases
2. Extract and run `BiometricIntegration.exe`

## Developer Setup

This app has two parts that run separately: a **Python backend** (the desktop window) and a **Vue.js frontend** (the UI). In dev mode they connect over localhost, so you need both running at the same time.

### Prerequisites

- **Python 3.10+** — check with `python3 --version`
- **Node.js 18+** — check with `node --version`
- **npm** — comes with Node.js
- **Git**

### 1. Clone the repo

```bash
git clone <repo-url>
cd integrator_sanbeda_taytay
```

### 2. Set up the backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### 3. Set up the frontend

```bash
cd frontend
npm install
```

### 4. Run in development mode

You need **two terminal windows** open at the same time.

**Terminal 1 — Frontend dev server:**
```bash
cd frontend
npm run dev
```
This starts Vite at `http://localhost:5173`. Keep it running.

**Terminal 2 — Backend (Python app):**
```bash
cd backend
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

python main.py
```

The app window will open. It loads the UI from the Vite dev server automatically. Logs print directly to Terminal 2 — this is where you see pull/push activity, errors, and database operations.

> **Note:** Press **F12** inside the app window to open Chrome DevTools for frontend debugging.

---

### Running the tests

**Backend tests (pytest):**
```bash
cd backend
source venv/bin/activate
pip install -r requirements-dev.txt   # one-time, installs pytest + pytest-mock
python -m pytest tests/ -v
```

**Frontend tests (vitest):**
```bash
cd frontend
npm test
```

---

### Optional: Mock API server

If you don't have access to the live YAHSHUA Payroll API, you can run a local mock server that simulates it:

```bash
cd backend
source venv/bin/activate
python mock_server.py
```

This starts a fake API at `http://localhost:8000`. In the app's **Configuration** tab, set the Push URL to `http://localhost:8000` to test the push flow without hitting the real server.

---

### Where data is stored

In dev mode the SQLite database is at:
```
backend/database/zkteco_integration.db
```

This is separate from the production database used by the installed app (`~/Library/Application Support/ZKTecoIntegration/` on macOS). Changes in dev don't affect production data and vice versa.

---

### Common issues

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: No module named 'PyQt6'` | Run `pip install -r requirements.txt` inside the venv |
| App window opens but shows blank/error | Make sure the Vite dev server (Terminal 1) is running on port 5173 |
| Port 5173 already in use | Kill the process: `lsof -ti:5173 \| xargs kill` |
| `pyzk` errors in tests | Normal — tests stub the ZK library. Run tests with `pytest` not `python` |
| macOS: "cannot be opened because the developer cannot be verified" | Right-click → Open, or run from terminal |

## Documentation

See **[CLAUDE.md](CLAUDE.md)** for comprehensive developer documentation including:
- Architecture overview
- ZKTeco device communication
- Database schema
- Build instructions
- Troubleshooting guide

## Release

```bash
git tag vX.X.X
git push origin vX.X.X
```

GitHub Actions will automatically build and create a release with macOS DMG and Windows ZIP.

## License

Copyright © 2025 The Abba. All rights reserved.
