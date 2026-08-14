#!/usr/bin/env bash
# Direct battery limit setter (Universal)

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
max="$1"

if [ -z "$max" ]; then
    echo "Usage: sudo ./limit.sh <limit>"
    echo "Example: sudo ./limit.sh 80"
    exit 1
fi

if [ "$EUID" -ne 0 ]; then
    echo "Error: Superuser (root) permissions required."
    echo "Please run: sudo ./limit.sh $max"
    exit 1
fi

# Run via backend if python3 is available
if command -v python3 &> /dev/null && [ -f "$SCRIPT_DIR/battery_limiter_backend.py" ]; then
    python3 "$SCRIPT_DIR/battery_limiter_backend.py" set "$max"
    exit $?
fi

# Pure bash fallback
APPLIED=0
for f in /sys/class/power_supply/*/charge_control_end_threshold /sys/class/power_supply/*/charge_stop_threshold; do
    if [ -f "$f" ]; then
        echo "$max" > "$f" && APPLIED=$((APPLIED + 1))
    fi
done

CONV_VAL=$([ "$max" -le 80 ] && echo 1 || echo 0)
for f in /sys/bus/platform/drivers/ideapad_acpi/*/conservation_mode \
         /sys/bus/platform/drivers/ideapad_laptop/*/conservation_mode \
         /sys/bus/platform/devices/VPC2004*/conservation_mode \
         /sys/devices/platform/VPC2004*/conservation_mode; do
    if [ -f "$f" ]; then
        echo "$CONV_VAL" > "$f" && APPLIED=$((APPLIED + 1))
    fi
done

if [ "$APPLIED" -gt 0 ]; then
    echo "Limit set to $max% ✓"
else
    echo "Error: No supported battery interface found."
    exit 1
fi
