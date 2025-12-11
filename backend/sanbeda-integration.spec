# -*- mode: python ; coding: utf-8 -*-
# Attendance Sync - PyInstaller Spec for macOS

import sys
from pathlib import Path

block_cipher = None

# Get absolute paths
backend_path = Path(SPECPATH)
project_path = backend_path.parent
frontend_dist = project_path / 'frontend' / 'dist'

a = Analysis(
    ['main.py'],
    pathex=[str(backend_path)],
    binaries=[],
    datas=[
        # Include frontend dist files
        (str(frontend_dist), 'frontend/dist'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebChannel',
        'requests',
        'schedule',
        'Crypto',
        'Crypto.PublicKey',
        'Crypto.PublicKey.RSA',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AttendanceSync',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AttendanceSync',
)

app = BUNDLE(
    coll,
    name='Attendance Sync.app',
    icon=str(project_path / 'icons' / 'icon.icns'),
    bundle_identifier='com.theabba.attendance-sync',
    info_plist={
        'CFBundleName': 'Attendance Sync',
        'CFBundleDisplayName': 'Attendance Sync',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.13.0',
    },
)
