#!/usr/bin/env bash
# OpenRC init script generator for battery limit (Universal)

limit="$1"

throw_err() {
    echo "${1:-Unknown error occurred} :("
    exit 1
}

check_val() {
    if ! echo "$limit" | grep -E -q '^[0-9]+$'; then
        echo "Enter a numeric max limit"
        return 1
    elif [ "$limit" -gt 100 ] || [ "$limit" -le 0 ]; then
        echo "Please enter a valid max limit between [1-100]"
        return 1
    fi
    return 0
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "You must run this script as root"
        return 1
    fi
    return 0
}

conv_val=$([ "$limit" -le 80 ] && echo 1 || echo 0)
lg_val=$([ "$limit" -le 80 ] && echo 80 || echo 100)
sams_val=$([ "$limit" -le 80 ] && echo 1 || echo 0)
sony_val=$([ "$limit" -le 50 ] && echo 50 || ([ "$limit" -le 80 ] && echo 80 || echo 0))
hw_val=$([ "$limit" -le 70 ] && echo "40 70" || ([ "$limit" -le 80 ] && echo "70 80" || echo "95 100"))

exec_cmd="for f in /sys/class/power_supply/*/charge_control_end_threshold /sys/class/power_supply/*/charge_stop_threshold /sys/class/power_supply/macsmc-battery/charge_control_limit_max; do [ -f \"\$f\" ] && echo $limit > \"\$f\" || true; done; for f in /sys/bus/platform/drivers/ideapad_acpi/*/conservation_mode /sys/bus/platform/drivers/ideapad_laptop/*/conservation_mode /sys/bus/platform/devices/VPC2004*/conservation_mode /sys/devices/platform/VPC2004*/conservation_mode; do [ -f \"\$f\" ] && echo $conv_val > \"\$f\" || true; done; for f in /sys/devices/platform/lg-laptop/battery_care_limit /sys/bus/platform/drivers/lg-laptop/*/battery_care_limit; do [ -f \"\$f\" ] && echo $lg_val > \"\$f\" || true; done; for f in /sys/devices/platform/samsung*/battery_life_extender; do [ -f \"\$f\" ] && echo $sams_val > \"\$f\" || true; done; for f in /sys/devices/platform/sony-laptop/battery_care_limiter; do [ -f \"\$f\" ] && echo $sony_val > \"\$f\" || true; done; for f in /sys/devices/platform/huawei-wmi/charge_thresholds; do [ -f \"\$f\" ] && echo \"$hw_val\" > \"\$f\" || true; done"

set_limit() {
    eval "$exec_cmd"
    echo "Max battery capacity is set to limit to $limit% $(tput setaf 2)✓$(tput sgr0)"
}

create_init() {
    cd /tmp || throw_err "Could not cd into /tmp"

    cat > batlimit << EOF
#!/sbin/openrc-run

name=\$RC_SVCNAME
description="limit battery charging"
command="/bin/bash"
command_args="-c '$exec_cmd'"
pidfile="/run/\${RC_SVCNAME}.pid"
EOF

    echo "init script creation complete $(tput setaf 2)✓$(tput sgr0)"
    chmod +x batlimit
    cp batlimit /etc/init.d/
    rc-update add batlimit default || throw_err "Could not add service to runlevel default"
    echo "OpenRC init script 'batlimit' added to runlevel default $(tput setaf 2)✓$(tput sgr0)"
}

if check_val && check_root; then
    set_limit
    create_init
else
    exit 1
fi
