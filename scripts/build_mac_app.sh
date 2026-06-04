#!/usr/bin/env bash
# Build "Organize My Beats.app" for macOS (double-click to launch, no terminal).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${ROOT}/.venv"
DIST="${ROOT}/dist"
ASSETS="${ROOT}/assets"
ICONSET="${ROOT}/build/AppIcon.iconset"
ICNS="${ASSETS}/AppIcon.icns"

cd "$ROOT"

if [[ ! -d "$VENV" ]]; then
  echo "Creating virtual environment..."
  python3 -m venv "$VENV"
fi

# shellcheck source=/dev/null
source "${VENV}/bin/activate"

echo "Installing build dependencies..."
pip install -q -U pip
pip install -q -e .
pip install -q pyinstaller

echo "Generating app icon..."
mkdir -p "$ICONSET" "$ASSETS"
ICON_32="${ASSETS}/icon_32.png"
ICON_64="${ASSETS}/icon_64.png"
ICON_96="${ASSETS}/icon_96.png"
MASTER_ICON="${ASSETS}/app_icon.png"
if [[ ! -f "$ICON_96" ]]; then
  echo "Missing icon files. Add icon_32.png, icon_64.png, and icon_96.png to assets/."
  exit 1
fi

python "${ROOT}/scripts/prepare_mac_icon.py" \
  "$MASTER_ICON" \
  "$ICONSET" \
  "$ICON_32" "$ICON_64" "$ICON_96"
iconutil -c icns "$ICONSET" -o "$ICNS"

echo "Building macOS app bundle..."
pyinstaller "${ROOT}/scripts/OrganizeMyBeats.spec" --noconfirm --clean

APP="${DIST}/Organize My Beats.app"
if [[ -d "$APP" ]]; then
  echo ""
  echo "Done! Your app is ready:"
  echo "  ${APP}"
  echo ""
  echo "To install: drag \"Organize My Beats.app\" into your Applications folder,"
  echo "then open it from Launchpad or Spotlight like any other Mac app."
else
  echo "Build failed — app bundle not found at ${APP}"
  exit 1
fi
