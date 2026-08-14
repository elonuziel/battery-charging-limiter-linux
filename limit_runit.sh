#!/usr/bin/env bash
# Runit init service generator for battery limit (Universal)

max="$1"

if [ -z "$max" ]; then
    echo "Usage: sudo ./limit_runit.sh <limit>"
    exit 1
fi

if ! echo "$max" | grep -E -q '^[0-9]+$' || [ "$max" -gt 100 ] || [ "$max" -le 0 ]; then
    echo "Please enter a valid max limit between [1-100]"
    exit 1
fi

conv_val=$([ "$max" -le 80 ] && echo 1 || echo 0)
lg_val=$([ "$max" -le 80 ] && echo 80 || echo 100)
sams_val=$([ "$max" -le 80 ] && echo 1 || echo 0)
sony_val=$([ "$max" -le 50 ] && echo 50 || ([ "$max" -le 80 ] && echo 80 || echo 0))
hw_val=$([ "$max" -le 70 ] && echo "40 70" || ([ "$max" -le 80 ] && echo "70 80" || echo "95 100"))

exec_cmd="for f in /sys/class/power_supply/*/charge_control_end_threshold /sys/class/power_supply/*/charge_stop_threshold /sys/class/power_supply/macsmc-battery/charge_control_limit_max; do [ -f \"\$f\" ] && echo $max > \"\$f\" || true; done; for f in /sys/bus/platform/drivers/ideapad_acpi/*/conservation_mode /sys/bus/platform/drivers/ideapad_laptop/*/conservation_mode /sys/bus/platform/devices/VPC2004*/conservation_mode /sys/devices/platform/VPC2004*/conservation_mode; do [ -f \"\$f\" ] && echo $conv_val > \"\$f\" || true; done; for f in /sys/devices/platform/lg-laptop/battery_care_limit /sys/bus/platform/drivers/lg-laptop/*/battery_care_limit; do [ -f \"\$f\" ] && echo $lg_val > \"\$f\" || true; done; for f in /sys/devices/platform/samsung*/battery_life_extender; do [ -f \"\$f\" ] && echo $sams_val > \"\$f\" || true; done; for f in /sys/devices/platform/sony-laptop/battery_care_limiter; do [ -f \"\$f\" ] && echo $sony_val > \"\$f\" || true; done; for f in /sys/devices/platform/huawei-wmi/charge_thresholds; do [ -f \"\$f\" ] && echo \"$hw_val\" > \"\$f\" || true; done"

eval "$exec_cmd"
echo "Max battery capacity is limiting to $max% $(tput setaf 2)✓$(tput sgr0)"

cd /tmp
cat > run << EOF
#!/bin/bash
$exec_cmd
EOF
chmod +x run

sudo mkdir -p /run/runit/service/battery-limit
sudo cp run /run/runit/service/battery-limit/

echo "Runit service configured ✓"
