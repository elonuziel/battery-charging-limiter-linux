#!/usr/bin/env bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
DESKTOP_MENU_DIR="$HOME/.local/share/applications"
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"

echo "Installing Battery Charge Limiter..."

# Ensure executable permissions
chmod +x "$SCRIPT_DIR/battery_limiter_gui.py"
chmod +x "$SCRIPT_DIR/battery_limiter_backend.py"
chmod +x "$SCRIPT_DIR/limit.sh"
chmod +x "$SCRIPT_DIR/limitd.sh"

DESKTOP_ENTRY="[Desktop Entry]
Name=Battery Charge Limiter
Comment=Protect laptop battery health by setting custom charge limit thresholds
Exec=/usr/bin/env python3 $SCRIPT_DIR/battery_limiter_gui.py
Icon=battery-good-charging
Terminal=false
Type=Application
Categories=Settings;HardwareSettings;System;GTK;
Keywords=battery;charge;limit;threshold;asus;laptop;health;
"

# 1. Install to Application Menu
mkdir -p "$DESKTOP_MENU_DIR"
echo "$DESKTOP_ENTRY" > "$DESKTOP_MENU_DIR/battery-limiter.desktop"
chmod +x "$DESKTOP_MENU_DIR/battery-limiter.desktop"

# 2. Install Shortcut on User Desktop
if [ -d "$DESKTOP_DIR" ]; then
    echo "$DESKTOP_ENTRY" > "$DESKTOP_DIR/battery-limiter.desktop"
    chmod +x "$DESKTOP_DIR/battery-limiter.desktop"
    if command -v gio &> /dev/null; then
        gio set "$DESKTOP_DIR/battery-limiter.desktop" metadata::trusted true 2>/dev/null || true
    fi
    echo "✓ Created desktop shortcut at: $DESKTOP_DIR/battery-limiter.desktop"
fi

echo "✓ Battery Charge Limiter installed successfully!"
echo "Launch from your desktop shortcut, application menu, or run:"
echo "  python3 $SCRIPT_DIR/battery_limiter_gui.py"
