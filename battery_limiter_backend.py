#!/usr/bin/env python3
"""
Battery Limiter Backend Helper for Linux.
Provides sysfs battery inspection, charge threshold application,
and systemd persistence configuration.
"""

import sys
import os
import glob
import subprocess
import json

SYSTEMD_SERVICE_PATH = "/etc/systemd/system/battery-manager.service"
HELPER_SCRIPT = "/usr/local/bin/battery-limiter-helper"


def find_battery_dirs():
    """Finds all battery sysfs directories containing charge_control_end_threshold."""
    bat_paths = []
    base_dir = "/sys/class/power_supply"
    if os.path.exists(base_dir):
        for entry in sorted(os.listdir(base_dir)):
            if entry.startswith("BAT"):
                thresh_file = os.path.join(base_dir, entry, "charge_control_end_threshold")
                if os.path.exists(thresh_file):
                    bat_paths.append(os.path.join(base_dir, entry))
    return bat_paths


def can_write_threshold():
    """Returns True if the current user can write to the threshold file directly (e.g. via udev plugdev rule)."""
    for bat_dir in find_battery_dirs():
        tf = os.path.join(bat_dir, "charge_control_end_threshold")
        if os.path.exists(tf) and os.access(tf, os.W_OK):
            return True
    return False


def get_battery_info():
    """Returns a dictionary with current battery capacity, status, threshold, and sysfs path."""
    bat_dirs = find_battery_dirs()
    bat_dir = bat_dirs[0] if bat_dirs else "/sys/class/power_supply/BAT0"

    def read(name):
        try:
            with open(os.path.join(bat_dir, name)) as f:
                return f.read().strip()
        except Exception:
            return None

    capacity_raw = read("capacity")
    capacity = int(capacity_raw) if capacity_raw and capacity_raw.isdigit() else None

    status = read("status") or "Unknown"
    manufacturer = read("manufacturer") or "Unknown"
    model = read("model_name") or "Unknown"

    threshold_raw = read("charge_control_end_threshold")
    threshold = int(threshold_raw) if threshold_raw and threshold_raw.isdigit() else None

    service_enabled = False
    if os.path.exists(SYSTEMD_SERVICE_PATH):
        try:
            res = subprocess.run(
                ["systemctl", "is-enabled", "battery-manager.service"],
                capture_output=True, text=True
            )
            service_enabled = (res.returncode == 0 and "enabled" in res.stdout)
        except Exception:
            pass

    # AC status
    ac_online = None
    for ac_path in glob.glob("/sys/class/power_supply/AC*"):
        online_file = os.path.join(ac_path, "online")
        if os.path.exists(online_file):
            try:
                with open(online_file) as f:
                    ac_online = f.read().strip() == "1"
                break
            except Exception:
                pass

    return {
        "bat_path": bat_dir,
        "capacity": capacity,
        "status": status,
        "threshold": threshold,
        "service_enabled": service_enabled,
        "manufacturer": manufacturer,
        "model": model,
        "ac_online": ac_online,
        "is_root": (os.geteuid() == 0),
        "can_write_direct": can_write_threshold(),
        "helper_installed": os.path.exists(HELPER_SCRIPT),
    }


def apply_limit_direct(limit):
    """Sets battery limit directly in sysfs. Requires write permission on threshold file."""
    try:
        limit = int(limit)
        if limit < 20 or limit > 100:
            return False, "Limit must be between 20 and 100"
    except (ValueError, TypeError):
        return False, "Limit must be an integer"

    bat_dirs = find_battery_dirs()
    if not bat_dirs:
        return False, "No battery with charge_control_end_threshold found in sysfs"

    written = []
    for bat_dir in bat_dirs:
        tf = os.path.join(bat_dir, "charge_control_end_threshold")
        try:
            with open(tf, "w") as f:
                f.write(f"{limit}\n")
            written.append(tf)
        except PermissionError:
            return False, f"Permission denied writing to {tf}. Root or plugdev group required."
        except Exception as e:
            return False, f"Error writing to {tf}: {e}"

    # Write systemd service for reboot persistence (only if root)
    if os.geteuid() == 0:
        _write_systemd_service(limit)

    return True, f"Successfully set charge limit to {limit}%! ({', '.join(written)})"


def _write_systemd_service(limit):
    """Creates and enables systemd service for reboot persistence."""
    service_content = f"""[Unit]
Description=Set battery charge threshold on boot and resume
After=multi-user.target suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'for f in /sys/class/power_supply/BAT*/charge_control_end_threshold; do echo {limit} > "$f"; done'

[Install]
WantedBy=multi-user.target suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target
"""
    try:
        with open(SYSTEMD_SERVICE_PATH, "w") as f:
            f.write(service_content)
        subprocess.run(["systemctl", "daemon-reload"], check=False, capture_output=True)
        subprocess.run(["systemctl", "enable", "battery-manager.service"], check=False, capture_output=True)
        subprocess.run(["systemctl", "start", "battery-manager.service"], check=False, capture_output=True)
    except Exception as e:
        print(f"Warning: Could not configure systemd service: {e}", file=sys.stderr)


def apply_limit(limit):
    """Primary entry point: apply limit directly (for root or plugdev access)."""
    return apply_limit_direct(limit)


def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "info":
            print(json.dumps(get_battery_info(), indent=2))
        elif cmd == "set" and len(sys.argv) > 2:
            success, msg = apply_limit(sys.argv[2])
            print(msg)
            sys.exit(0 if success else 1)
        else:
            print("Usage: battery_limiter_backend.py [info | set <limit>]")
            sys.exit(1)
    else:
        print(json.dumps(get_battery_info(), indent=2))


if __name__ == "__main__":
    main()
