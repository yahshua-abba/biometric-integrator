# Attendance Sync

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
1. Download `AttendanceSync-vX.X.X.dmg` from Releases
2. Open DMG and drag to Applications
3. First launch takes 1-2 minutes (one-time initialization)

### Windows
1. Download `AttendanceSync-vX.X.X-Windows.zip` from Releases
2. Extract and run `AttendanceSync.exe`

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
