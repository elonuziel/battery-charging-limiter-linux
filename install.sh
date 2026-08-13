#!/usr/bin/env bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
DESKTOP_DIR="$HOME/.local/share/applications"

echo "Installing Battery Charge Limiter..."

# Ensure executable permissions
chmod +x "$SCRIPT_DIR/battery_limiter_gui.py"
chmod +x "$SCRIPT_DIR/battery_limiter_backend.py"
chmod +x "$SCRIPT_DIR/limit.sh"
chmod +x "$SCRIPT_DIR/limitd.sh"

# Update desktop file path
mkdir -p "$DESKTOP_DIR"
cat <<EOF > "$DESKTOP_DIR/battery-limiter.desktop"
[Desktop Entry]
Name=Battery Charge Limiter
Comment=Protect laptop battery health by setting custom charge limit thresholds
Exec=/usr/bin/env python3 $SCRIPT_DIR/battery_limiter_gui.py
Icon=battery-good-charging
Terminal=false
Type=Application
Categories=Settings;HardwareSettings;System;GTK;
Keywords=battery;charge;limit;threshold;asus;laptop;health;
EOF

chmod +x "$DESKTOP_DIR/battery-limiter.desktop"

echo "✓ Battery Charge Limiter installed successfully!"
echo "You can now launch 'Battery Charge Limiter' from your application menu or run:"
echo "  python3 $SCRIPT_DIR/battery_limiter_gui.py"
