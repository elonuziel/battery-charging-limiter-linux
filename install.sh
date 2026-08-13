#!/usr/bin/env bash
# Battery Charge Limiter - Installer
# Must be run with sudo: sudo ./install.sh
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(eval echo "~$REAL_USER")
DESKTOP_DIR="$(sudo -u "$REAL_USER" xdg-user-dir DESKTOP 2>/dev/null || echo "$REAL_HOME/Desktop")"

echo "═══════════════════════════════════════════════════"
echo " Battery Charge Limiter Installer"
echo " ASUS UX331UA / Ubuntu 26.04"
echo "═══════════════════════════════════════════════════"

# ── 1. Ensure scripts are executable ────────────────────────────────────────
chmod +x "$SCRIPT_DIR/battery_limiter_gui.py"
chmod +x "$SCRIPT_DIR/battery_limiter_backend.py"
chmod +x "$SCRIPT_DIR/battery-limiter-helper"
chmod +x "$SCRIPT_DIR/limit.sh"
chmod +x "$SCRIPT_DIR/limitd.sh"
echo "✓ Script permissions set"

# ── 2. Install shell helper to system path (needed by pkexec polkit policy) ─
install -m 755 "$SCRIPT_DIR/battery-limiter-helper" /usr/local/bin/battery-limiter-helper
echo "✓ Installed helper to /usr/local/bin/battery-limiter-helper"

# ── 3. Install polkit policy ─────────────────────────────────────────────────
install -m 644 "$SCRIPT_DIR/com.battery.limiter.policy" /usr/share/polkit-1/actions/
echo "✓ Installed polkit policy"

# ── 4. Install udev rule (grants plugdev group write access at boot) ─────────
install -m 644 "$SCRIPT_DIR/85-battery-charge-limiter.rules" /etc/udev/rules.d/
udevadm control --reload-rules
udevadm trigger --subsystem-match=power_supply --action=change
echo "✓ Installed udev rule and reloaded"

# ── 5. Apply immediately without waiting for reboot ──────────────────────────
sleep 1
for THRESH_FILE in /sys/class/power_supply/BAT*/charge_control_end_threshold; do
    if [ -f "$THRESH_FILE" ]; then
        chmod g+w "$THRESH_FILE"
        chgrp plugdev "$THRESH_FILE"
        echo "✓ Applied plugdev group write access to $THRESH_FILE"
    fi
done

# ── 6. Install desktop menu entry ────────────────────────────────────────────
DESKTOP_MENU_DIR="$REAL_HOME/.local/share/applications"
mkdir -p "$DESKTOP_MENU_DIR"
cat > "$DESKTOP_MENU_DIR/battery-limiter.desktop" << EOF
[Desktop Entry]
Name=Battery Charge Limiter
Comment=Protect laptop battery health by setting custom charge limit thresholds
Exec=/usr/bin/python3 $SCRIPT_DIR/battery_limiter_gui.py
Icon=battery-good-charging
Terminal=false
Type=Application
Categories=Settings;HardwareSettings;System;GTK;
Keywords=battery;charge;limit;threshold;asus;laptop;health;
EOF
chown "$REAL_USER:$REAL_USER" "$DESKTOP_MENU_DIR/battery-limiter.desktop"
chmod +x "$DESKTOP_MENU_DIR/battery-limiter.desktop"
echo "✓ Installed application menu entry"

# ── 7. Install desktop shortcut ──────────────────────────────────────────────
if [ -d "$DESKTOP_DIR" ]; then
    cat > "$DESKTOP_DIR/battery-limiter.desktop" << EOF
[Desktop Entry]
Name=Battery Charge Limiter
Comment=Protect laptop battery health by setting custom charge limit thresholds
Exec=/usr/bin/python3 $SCRIPT_DIR/battery_limiter_gui.py
Icon=battery-good-charging
Terminal=false
Type=Application
Categories=Settings;HardwareSettings;System;GTK;
Keywords=battery;charge;limit;threshold;asus;laptop;health;
EOF
    chown "$REAL_USER:$REAL_USER" "$DESKTOP_DIR/battery-limiter.desktop"
    chmod +x "$DESKTOP_DIR/battery-limiter.desktop"
    sudo -u "$REAL_USER" gio set "$DESKTOP_DIR/battery-limiter.desktop" metadata::trusted true 2>/dev/null || true
    echo "✓ Created Desktop shortcut: $DESKTOP_DIR/battery-limiter.desktop"
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo " ✅ Installation complete!"
echo ""
echo " You can now use the app WITHOUT a password."
echo " Launch it from your Desktop icon or run:"
echo "   python3 $SCRIPT_DIR/battery_limiter_gui.py"
echo "═══════════════════════════════════════════════════"
