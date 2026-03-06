#!/bin/bash
# Local macOS build script — mirrors CI pipeline
# Produces a DMG installer in ./dist/

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
BUILD_VENV="$BACKEND_DIR/.build_venv"

# Use Python 3.10 to match CI
PYTHON="/opt/homebrew/bin/python3.10"

# Determine version from git tag
VERSION=$(git -C "$SCRIPT_DIR" describe --tags --abbrev=0 2>/dev/null | sed 's/^v//' || echo "0.0.0-local")

echo "========================================="
echo "Local macOS Build"
echo "Version: $VERSION"
echo "========================================="

# 1. Build frontend
echo ""
echo "[1/4] Building frontend..."
cd "$FRONTEND_DIR"
npm install --silent
npm run build
echo "Frontend built → frontend/dist/"

# 2. Set up isolated build venv with Python 3.10
echo ""
echo "[2/4] Setting up Python 3.10 build environment..."
if [ ! -d "$BUILD_VENV" ]; then
    "$PYTHON" -m venv "$BUILD_VENV"
    echo "Created build venv at $BUILD_VENV"
fi
source "$BUILD_VENV/bin/activate"

pip install --quiet --upgrade pip
pip install --quiet pyinstaller
pip install --quiet -r "$BACKEND_DIR/requirements.txt"
echo "Dependencies installed"

# 3. Write VERSION file and run PyInstaller
echo ""
echo "[3/4] Building app with PyInstaller..."
cd "$BACKEND_DIR"
echo "$VERSION" > VERSION
pyinstaller --clean -y --distpath "$SCRIPT_DIR/dist" --workpath "$BACKEND_DIR/build" sanbeda-integration.spec
echo "PyInstaller done → dist/Biometric Integration.app"

deactivate

# 4. Create DMG
echo ""
echo "[4/4] Creating DMG..."
chmod +x "$BACKEND_DIR/create_dmg.sh"
"$BACKEND_DIR/create_dmg.sh" "$VERSION"

echo ""
echo "Done! DMG is at: dist/BiometricIntegration-v${VERSION}.dmg"
