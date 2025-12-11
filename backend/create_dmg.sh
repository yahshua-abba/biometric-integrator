#!/bin/bash
# Biometric Integration - DMG Installer Creator for macOS

set -e

APP_NAME="Biometric Integration"
VERSION="${1:-1.0.0}"  # Accept version as argument, default to 1.0.0
DMG_NAME="BiometricIntegration-v${VERSION}.dmg"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Check for app in multiple locations (CI vs local build)
if [ -d "${PROJECT_DIR}/dist/${APP_NAME}.app" ]; then
    # CI build: app is in project root /dist/
    APP_PATH="${PROJECT_DIR}/dist/${APP_NAME}.app"
    DMG_PATH="${PROJECT_DIR}/dist/${DMG_NAME}"
elif [ -d "${SCRIPT_DIR}/dist/${APP_NAME}.app" ]; then
    # Local build: app is in backend/dist/
    APP_PATH="${SCRIPT_DIR}/dist/${APP_NAME}.app"
    DMG_PATH="${SCRIPT_DIR}/dist/${DMG_NAME}"
else
    echo "Error: Application not found"
    echo "Searched in:"
    echo "  - ${PROJECT_DIR}/dist/${APP_NAME}.app"
    echo "  - ${SCRIPT_DIR}/dist/${APP_NAME}.app"
    echo "Please run PyInstaller first"
    exit 1
fi

echo "========================================="
echo "Creating DMG Installer"
echo "========================================="
echo "App: $APP_PATH"

# Remove old DMG if exists
if [ -f "$DMG_PATH" ]; then
    echo "Removing old DMG..."
    rm "$DMG_PATH"
fi

# Create temporary directory
TEMP_DIR=$(mktemp -d)
echo "Creating temporary directory at $TEMP_DIR"

# Copy app to temp directory
echo "Copying application..."
cp -R "$APP_PATH" "$TEMP_DIR/"

# Create symlink to Applications folder
echo "Creating Applications symlink..."
ln -s /Applications "$TEMP_DIR/Applications"

# Create DMG
echo "Creating DMG..."
hdiutil create -volname "${APP_NAME}" \
    -srcfolder "$TEMP_DIR" \
    -ov -format UDZO \
    "$DMG_PATH"

# Clean up
echo "Cleaning up..."
rm -rf "$TEMP_DIR"

# Get DMG size
DMG_SIZE=$(du -h "$DMG_PATH" | cut -f1)

echo ""
echo "========================================="
echo "DMG created successfully!"
echo "========================================="
echo "Location: $DMG_PATH"
echo "Size: $DMG_SIZE"
echo ""
echo "To distribute:"
echo "1. Test the DMG by mounting and dragging to Applications"
echo "2. Upload to your distribution server"
echo "========================================="
