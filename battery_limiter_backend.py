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

def find_battery_paths():
    """Finds all battery sysfs directories containing charge_control_end_threshold."""
    bat_paths = []
    base_dir = "/sys/class/power_supply"
    if os.path.exists(base_dir):
        for entry in os.listdir(base_dir):
            if entry.startswith("BAT"):
                thresh_file = os.path.join(base_dir, entry, "charge_control_end_threshold")
                if os.path.exists(thresh_file):
                    bat_paths.append(os.path.join(base_dir, entry))
    return bat_paths

def get_battery_info():
    """Returns a dictionary with current battery capacity, status, threshold, and sysfs path."""
    bat_paths = find_battery_paths()
    if not bat_paths:
        # Fallback check for any BAT directory
        bat_paths = glob.glob("/sys/class/power_supply/BAT*")
    
    bat_dir = bat_paths[0] if bat_paths else "/sys/class/power_supply/BAT0"
    
    capacity = None
    status = "Unknown"
    threshold = None
    
    cap_file = os.path.join(bat_dir, "capacity")
    if os.path.exists(cap_file):
        try:
            with open(cap_file, "r") as f:
                capacity = int(f.read().strip())
        except Exception:
            pass
            
    stat_file = os.path.join(bat_dir, "status")
    if os.path.exists(stat_file):
        try:
            with open(stat_file, "r") as f:
                status = f.read().strip()
        except Exception:
            pass

    thresh_file = os.path.join(bat_dir, "charge_control_end_threshold")
    if os.path.exists(thresh_file):
        try:
            with open(thresh_file, "r") as f:
                threshold = int(f.read().strip())
        except Exception:
            pass

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

    return {
        "bat_path": bat_dir,
        "capacity": capacity,
        "status": status,
        "threshold": threshold,
        "service_enabled": service_enabled,
        "is_root": (os.geteuid() == 0)
    }

def apply_limit(limit):
    """Sets battery limit in sysfs and enables systemd service for reboot persistence."""
    try:
        limit = int(limit)
        if limit < 20 or limit > 100:
            return False, "Limit must be between 20 and 100"
    except ValueError:
        return False, "Limit must be an integer"

    # Find threshold files
    thresh_files = glob.glob("/sys/class/power_supply/BAT*/charge_control_end_threshold")
    if not thresh_files:
        thresh_files = ["/sys/class/power_supply/BAT0/charge_control_end_threshold"]

    written = False
    for tf in thresh_files:
        try:
            with open(tf, "w") as f:
                f.write(f"{limit}\n")
            written = True
        except Exception as e:
            return False, f"Failed to write to {tf}: {e}. Root permissions required."

    # Create systemd service
    service_content = f"""[Unit]
Description=To set battery charge threshold on boot/resume
After=multi-user.target suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'echo {limit} > /sys/class/power_supply/BAT?/charge_control_end_threshold'

[Install]
WantedBy=multi-user.target suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target
"""
    try:
        with open(SYSTEMD_SERVICE_PATH, "w") as f:
            f.write(service_content)
        
        subprocess.run(["systemctl", "daemon-reload"], check=False)
        subprocess.run(["systemctl", "enable", "battery-manager.service"], check=False)
    except Exception as e:
        return False, f"Limit set to {limit}%, but failed to create systemd service: {e}"

    return True, f"Successfully set charge limit to {limit}% and enabled systemd reboot persistence!"

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
    else:
        print(json.dumps(get_battery_info(), indent=2))

if __name__ == "__main__":
    main()
