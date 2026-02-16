# -*- mode: python ; coding: utf-8 -*-
# Biometric Integration - PyInstaller Spec for Windows

import sys
from pathlib import Path

block_cipher = None

# Get absolute paths
backend_path = Path(SPECPATH)
project_path = backend_path.parent
frontend_dist = project_path / 'frontend' / 'dist'

# Read version from VERSION file (written by CI)
version_file = backend_path / 'VERSION'
app_version = '0.0.0'
if version_file.exists():
    app_version = version_file.read_text().strip()

a = Analysis(
    ['main.py'],
    pathex=[str(backend_path)],
    binaries=[],
    datas=[
        # Include frontend dist files
        (str(frontend_dist), 'frontend/dist'),
        # Include VERSION file for runtime version detection
        (str(backend_path / 'VERSION'), '.'),
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BiometricIntegration',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_path / 'icons' / 'icon.ico'),
)
