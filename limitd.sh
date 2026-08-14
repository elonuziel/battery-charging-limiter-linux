#!/usr/bin/env bash
# Set battery charging limit with systemd persistence (Universal)

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
max="$1"

if [ -z "$max" ]; then
    echo "Usage: sudo ./limitd.sh <limit>"
    echo "Example: sudo ./limitd.sh 80"
    exit 1
fi

if [ "$EUID" -ne 0 ]; then
    echo "Error: Superuser (root) permissions required."
    echo "Please run: sudo ./limitd.sh $max"
    exit 1
fi

# Run via backend if python3 is available
if command -v python3 &> /dev/null && [ -f "$SCRIPT_DIR/battery_limiter_backend.py" ]; then
    python3 "$SCRIPT_DIR/battery_limiter_backend.py" set "$max"
    exit $?
fi

# Pure bash fallback
conv_val=$([ "$max" -le 80 ] && echo 1 || echo 0)
lg_val=$([ "$max" -le 80 ] && echo 80 || echo 100)
sams_val=$([ "$max" -le 80 ] && echo 1 || echo 0)
sony_val=$([ "$max" -le 50 ] && echo 50 || ([ "$max" -le 80 ] && echo 80 || echo 0))
hw_val=$([ "$max" -le 70 ] && echo "40 70" || ([ "$max" -le 80 ] && echo "70 80" || echo "95 100"))

exec_cmd="/bin/bash -c 'for f in /sys/class/power_supply/*/charge_control_end_threshold /sys/class/power_supply/*/charge_stop_threshold /sys/class/power_supply/macsmc-battery/charge_control_limit_max; do [ -f \"\$f\" ] && echo $max > \"\$f\" || true; done; for f in /sys/bus/platform/drivers/ideapad_acpi/*/conservation_mode /sys/bus/platform/drivers/ideapad_laptop/*/conservation_mode /sys/bus/platform/devices/VPC2004*/conservation_mode /sys/devices/platform/VPC2004*/conservation_mode; do [ -f \"\$f\" ] && echo $conv_val > \"\$f\" || true; done; for f in /sys/devices/platform/lg-laptop/battery_care_limit /sys/bus/platform/drivers/lg-laptop/*/battery_care_limit; do [ -f \"\$f\" ] && echo $lg_val > \"\$f\" || true; done; for f in /sys/devices/platform/samsung*/battery_life_extender; do [ -f \"\$f\" ] && echo $sams_val > \"\$f\" || true; done; for f in /sys/devices/platform/sony-laptop/battery_care_limiter; do [ -f \"\$f\" ] && echo $sony_val > \"\$f\" || true; done; for f in /sys/devices/platform/huawei-wmi/charge_thresholds; do [ -f \"\$f\" ] && echo \"$hw_val\" > \"\$f\" || true; done'"

# Apply immediately
eval "$exec_cmd"

cat > /etc/systemd/system/battery-manager.service << EOF
[Unit]
Description=Set battery charge threshold on boot and resume
After=multi-user.target suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target

[Service]
Type=oneshot
ExecStart=$exec_cmd

[Install]
WantedBy=multi-user.target suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target
EOF

systemctl daemon-reload
systemctl enable battery-manager.service
systemctl start battery-manager.service 2>/dev/null || true

echo "Successfully set battery charge threshold to $max% and enabled systemd reboot persistence! ✓"
