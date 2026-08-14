#!/usr/bin/env bash
# Battery Charge Limiter - Universal Installer
# Must be run with sudo: sudo ./install.sh
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(eval echo "~$REAL_USER")
DESKTOP_DIR="$(sudo -u "$REAL_USER" xdg-user-dir DESKTOP 2>/dev/null || echo "$REAL_HOME/Desktop")"

echo "═══════════════════════════════════════════════════"
echo " Battery Charge Limiter Installer"
echo " Universal Linux Laptop Support"
echo "═══════════════════════════════════════════════════"

# ── 1. Ensure scripts are executable ────────────────────────────────────────
chmod +x "$SCRIPT_DIR/battery_limiter_gui.py"
chmod +x "$SCRIPT_DIR/battery_limiter_backend.py"
chmod +x "$SCRIPT_DIR/battery-limiter-helper"
chmod +x "$SCRIPT_DIR/limit.sh"
chmod +x "$SCRIPT_DIR/limitd.sh"
chmod +x "$SCRIPT_DIR/limitrc.sh"
chmod +x "$SCRIPT_DIR/limit_runit.sh"
echo "✓ Script permissions set"

# ── 2. Install shell helper to system path (needed by pkexec polkit policy) ─
install -m 755 "$SCRIPT_DIR/battery-limiter-helper" /usr/local/bin/battery-limiter-helper
echo "✓ Installed helper to /usr/local/bin/battery-limiter-helper"

# ── 3. Install polkit policy ─────────────────────────────────────────────────
install -m 644 "$SCRIPT_DIR/com.battery.limiter.policy" /usr/share/polkit-1/actions/
echo "✓ Installed polkit policy"

# ── 4. Install udev rule (grants plugdev group write access at boot) ─────────
install -m 644 "$SCRIPT_DIR/85-battery-charge-limiter.rules" /etc/udev/rules.d/
udevadm control --reload-rules 2>/dev/null || true
udevadm trigger --subsystem-match=power_supply 2>/dev/null || true
udevadm trigger --subsystem-match=platform 2>/dev/null || true
echo "✓ Installed udev rules and reloaded"

# ── 5. Apply permissions immediately without waiting for reboot ──────────────
NODES_FOUND=0

# Standard power_supply threshold files
for THRESH_FILE in /sys/class/power_supply/*/charge_control_end_threshold \
                   /sys/class/power_supply/*/charge_control_start_threshold \
                   /sys/class/power_supply/*/charge_stop_threshold \
                   /sys/class/power_supply/*/charge_start_threshold \
                   /sys/class/power_supply/macsmc-battery/charge_control_limit_max; do
    if [ -f "$THRESH_FILE" ]; then
        chmod g+w "$THRESH_FILE" 2>/dev/null || true
        chgrp plugdev "$THRESH_FILE" 2>/dev/null || true
        echo "✓ Applied plugdev group write access to $THRESH_FILE"
        NODES_FOUND=$((NODES_FOUND + 1))
    fi
done

# Lenovo conservation_mode
for CONV_FILE in /sys/bus/platform/drivers/ideapad_acpi/*/conservation_mode \
                 /sys/bus/platform/drivers/ideapad_laptop/*/conservation_mode \
                 /sys/bus/platform/devices/VPC2004*/conservation_mode \
                 /sys/devices/platform/VPC2004*/conservation_mode; do
    if [ -f "$CONV_FILE" ]; then
        chmod g+w "$CONV_FILE" 2>/dev/null || true
        chgrp plugdev "$CONV_FILE" 2>/dev/null || true
        echo "✓ Applied plugdev group write access to Lenovo $CONV_FILE"
        NODES_FOUND=$((NODES_FOUND + 1))
    fi
done

# LG, Samsung, Sony, Huawei
for VENDOR_FILE in /sys/devices/platform/lg-laptop/battery_care_limit \
                   /sys/bus/platform/drivers/lg-laptop/*/battery_care_limit \
                   /sys/devices/platform/samsung*/battery_life_extender \
                   /sys/bus/platform/drivers/samsung*/battery_life_extender \
                   /sys/devices/platform/sony-laptop/battery_care_limiter \
                   /sys/devices/platform/huawei-wmi/charge_thresholds; do
    if [ -f "$VENDOR_FILE" ]; then
        chmod g+w "$VENDOR_FILE" 2>/dev/null || true
        chgrp plugdev "$VENDOR_FILE" 2>/dev/null || true
        echo "✓ Applied plugdev group write access to $VENDOR_FILE"
        NODES_FOUND=$((NODES_FOUND + 1))
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
Keywords=battery;charge;limit;threshold;lenovo;asus;dell;laptop;health;
EOF
chown "$REAL_USER:$REAL_USER" "$DESKTOP_MENU_DIR/battery-limiter.desktop"
chmod +x "$DESKTOP_MENU_DIR/battery-limiter.desktop"
echo "✓ Installed application menu entry: $DESKTOP_MENU_DIR/battery-limiter.desktop"

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
Keywords=battery;charge;limit;threshold;lenovo;asus;dell;laptop;health;
EOF
    chown "$REAL_USER:$REAL_USER" "$DESKTOP_DIR/battery-limiter.desktop"
    chmod +x "$DESKTOP_DIR/battery-limiter.desktop"
    sudo -u "$REAL_USER" gio set "$DESKTOP_DIR/battery-limiter.desktop" metadata::trusted true 2>/dev/null || true
    echo "✓ Created Desktop shortcut: $DESKTOP_DIR/battery-limiter.desktop"
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo " 🔍 Detected Hardware Configuration:"
python3 "$SCRIPT_DIR/battery_limiter_backend.py" status || true
echo "═══════════════════════════════════════════════════"
echo " ✅ Installation complete!"
echo ""
echo " Launch the GUI from your application menu or run:"
echo "   python3 $SCRIPT_DIR/battery_limiter_gui.py"
echo "═══════════════════════════════════════════════════"
