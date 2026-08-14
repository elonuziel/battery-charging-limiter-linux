#!/usr/bin/env python3
"""
Battery Limiter Backend Helper for Linux.
Hardware-accurate detection and charge threshold management supporting:
- Lenovo IdeaPad, ThinkBook, Yoga, Legion, Xiaoxin (via ideapad_laptop conservation_mode: 60% vs 100%)
- ASUS laptops (ROG, TUF, ZenBook, VivoBook via asus_wmi: 60%, 80%, 100% or granular)
- Lenovo ThinkPad (via thinkpad_acpi charge_control_end_threshold)
- LG Gram (via lg_laptop battery_care_limit: 80% vs 100%)
- Samsung laptops / Galaxy Book (via samsung_laptop battery_life_extender: 80% vs 100%)
- Sony Vaio (via sony_laptop battery_care_limiter: 50%, 80%, 100%)
- Huawei MateBook (via huawei_wmi charge_thresholds: 70%, 80%, 100%)
- Dell, Framework, System76/Clevo, MSI, Toshiba, Apple Silicon Mac (Linux Kernel 5.4+ sysfs)
"""

import sys
import os
import glob
import subprocess
import json

SYSTEMD_SERVICE_PATH = "/etc/systemd/system/battery-manager.service"
HELPER_SCRIPT = "/usr/local/bin/battery-limiter-helper"


def read_file(path):
    """Safely reads a sysfs file and strips whitespace."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return None


def read_int(path):
    """Safely reads an integer from a sysfs file."""
    s = read_file(path)
    if s and s.lstrip("-").isdigit():
        return int(s)
    return None


def get_laptop_info():
    """Reads DMI system information to identify the laptop vendor and model."""
    dmi_dir = "/sys/class/dmi/id"
    vendor = read_file(os.path.join(dmi_dir, "sys_vendor")) or "Unknown"
    prod_name = read_file(os.path.join(dmi_dir, "product_name")) or ""
    prod_ver = read_file(os.path.join(dmi_dir, "product_version")) or ""
    board_name = read_file(os.path.join(dmi_dir, "board_name")) or ""

    vendor_clean = vendor.strip() if vendor != "Unknown" else "Linux Laptop"
    model = ""
    if prod_ver and prod_ver not in ("None", "Default string", "System Version", vendor):
        model = prod_ver.strip()
        if prod_name and prod_name not in ("None", "Default string", "System Product Name", vendor, model):
            model += f" ({prod_name})"
    elif prod_name and prod_name not in ("None", "Default string", "System Product Name", vendor):
        model = prod_name.strip()
    elif board_name and board_name not in ("None", "Default string", vendor):
        model = board_name.strip()

    display_name = f"{vendor_clean} {model}".strip() if model else vendor_clean

    return {
        "vendor": vendor,
        "product_name": prod_name,
        "product_version": prod_ver,
        "board_name": board_name,
        "display_name": display_name,
    }


def find_battery_devices():
    """Finds all battery devices under /sys/class/power_supply."""
    base_dir = "/sys/class/power_supply"
    batteries = []

    if os.path.exists(base_dir):
        for entry in sorted(os.listdir(base_dir)):
            bat_path = os.path.join(base_dir, entry)
            dev_type = read_file(os.path.join(bat_path, "type"))
            if dev_type == "Battery" or entry.startswith("BAT") or "battery" in entry.lower() or entry == "macsmc-battery":
                batteries.append(bat_path)

    return batteries


def detect_control_interface():
    """
    Detects the active battery charge limiting interface on this machine.
    Returns a dictionary describing the interface type, driver name, file paths, and genuine hardware capabilities.
    """
    bat_devices = find_battery_devices()

    # 1. Check for standard power_supply charge thresholds (ASUS, ThinkPad, Dell, Framework, System76, MSI, etc.)
    std_thresh_files = []
    for bat_dir in bat_devices:
        for fname in ["charge_control_end_threshold", "charge_stop_threshold", "charge_control_limit_max"]:
            tf = os.path.join(bat_dir, fname)
            if os.path.exists(tf):
                std_thresh_files.append(tf)

    if std_thresh_files:
        return {
            "type": "percentage",
            "driver_name": "Standard ACPI / Vendor WMI (charge_control_end_threshold)",
            "paths": std_thresh_files,
            "supports_slider": True,
            "min_limit": 20,
            "max_limit": 100,
            "step": 5,
            "hardware_note": "Your laptop hardware supports continuous integer charge threshold percentages.",
            "presets": [
                {
                    "value": 60,
                    "label": "🌿 Maximum Lifespan (60%)",
                    "badge": "DESK USE",
                    "desc": "Recommended for always-plugged-in desk work. Keeps battery at 60% to minimize cell voltage stress & heat build-up."
                },
                {
                    "value": 80,
                    "label": "⚖️ Daily Balance (80%)",
                    "badge": "RECOMMENDED",
                    "desc": "Recommended for daily mixed use. Balances chemical longevity with sufficient mobile battery run-time."
                },
                {
                    "value": 100,
                    "label": "✈️ Full Capacity (100%)",
                    "badge": "FULL CHARGE",
                    "desc": "For travel, flights, or long off-grid work. Charges battery to full 100% capacity."
                },
            ],
        }

    # 2. Check for Lenovo IdeaPad / ThinkBook / Yoga / Legion / Xiaoxin (conservation_mode)
    lenovo_candidates = (
        glob.glob("/sys/bus/platform/drivers/ideapad_acpi/*/conservation_mode")
        + glob.glob("/sys/bus/platform/drivers/ideapad_laptop/*/conservation_mode")
        + glob.glob("/sys/bus/platform/devices/VPC2004*/conservation_mode")
        + glob.glob("/sys/devices/platform/VPC2004*/conservation_mode")
    )
    lenovo_paths = sorted(list(set([os.path.realpath(p) for p in lenovo_candidates if os.path.exists(p)])))
    if lenovo_paths:
        return {
            "type": "conservation_mode",
            "driver_name": "Lenovo IdeaPad ACPI (conservation_mode)",
            "paths": lenovo_paths,
            "supports_slider": False,
            "min_limit": 60,
            "max_limit": 100,
            "step": 40,
            "hardware_note": "Your Lenovo ThinkBook uses Embedded Controller (EC) Conservation Mode. The firmware physically supports two hardware states: Conservation Mode (~55-60%) and Full Charge (100%).",
            "presets": [
                {
                    "value": 60,
                    "label": "🌿 Conservation Mode (~60%)",
                    "badge": "MAX LIFESPAN",
                    "desc": "Activates Lenovo Conservation Mode. Embedded Controller hardware automatically regulates charge between ~55% and ~60% to prevent chemical wear while plugged into AC power."
                },
                {
                    "value": 100,
                    "label": "✈️ Full Capacity (100%)",
                    "badge": "FULL MOBILITY",
                    "desc": "Disables conservation mode. Battery charges to full 100% capacity for travel, flights, and extended mobile off-grid work."
                },
            ],
        }

    # 3. Check for LG Gram (battery_care_limit: 80 or 100)
    lg_candidates = (
        glob.glob("/sys/devices/platform/lg-laptop/battery_care_limit")
        + glob.glob("/sys/bus/platform/drivers/lg-laptop/*/battery_care_limit")
        + glob.glob("/sys/bus/platform/devices/lg-laptop/battery_care_limit")
    )
    lg_paths = sorted(list(set([os.path.realpath(p) for p in lg_candidates if os.path.exists(p)])))
    if lg_paths:
        return {
            "type": "lg_care",
            "driver_name": "LG Laptop ACPI (battery_care_limit)",
            "paths": lg_paths,
            "supports_slider": False,
            "min_limit": 80,
            "max_limit": 100,
            "step": 20,
            "hardware_note": "LG Gram hardware provides two modes: Battery Care (80%) and Full Charge (100%).",
            "presets": [
                {"value": 80, "label": "🌿 Battery Care (80%)", "badge": "BATTERY CARE", "desc": "Caps charge at 80% to prolong battery lifespan."},
                {"value": 100, "label": "✈️ Full Capacity (100%)", "badge": "FULL CHARGE", "desc": "Charges battery to full 100% capacity."},
            ],
        }

    # 4. Check for Samsung laptops (battery_life_extender: 1 for 80%, 0 for 100%)
    samsung_candidates = (
        glob.glob("/sys/devices/platform/samsung*/battery_life_extender")
        + glob.glob("/sys/bus/platform/drivers/samsung*/battery_life_extender")
        + glob.glob("/sys/bus/platform/devices/samsung*/battery_life_extender")
    )
    samsung_paths = sorted(list(set([os.path.realpath(p) for p in samsung_candidates if os.path.exists(p)])))
    if samsung_paths:
        return {
            "type": "samsung_extender",
            "driver_name": "Samsung Battery Life Extender",
            "paths": samsung_paths,
            "supports_slider": False,
            "min_limit": 80,
            "max_limit": 100,
            "step": 20,
            "hardware_note": "Samsung hardware provides two modes: Life Extender (80%) and Full Charge (100%).",
            "presets": [
                {"value": 80, "label": "🌿 Battery Life Extender (80%)", "badge": "EXTENDER", "desc": "Caps maximum charge to 80% to protect battery health."},
                {"value": 100, "label": "✈️ Full Capacity (100%)", "badge": "FULL CHARGE", "desc": "Charges to 100% capacity."},
            ],
        }

    # 5. Check for Sony Vaio (battery_care_limiter: 0=100, 50=50, 80=80)
    sony_candidates = (
        glob.glob("/sys/devices/platform/sony-laptop/battery_care_limiter")
        + glob.glob("/sys/bus/platform/devices/sony-laptop/battery_care_limiter")
    )
    sony_paths = sorted(list(set([os.path.realpath(p) for p in sony_candidates if os.path.exists(p)])))
    if sony_paths:
        return {
            "type": "sony_care",
            "driver_name": "Sony Vaio Battery Care Limiter",
            "paths": sony_paths,
            "supports_slider": False,
            "min_limit": 50,
            "max_limit": 100,
            "step": 30,
            "hardware_note": "Sony Vaio hardware provides three modes: 50%, 80%, and Full 100%.",
            "presets": [
                {"value": 50, "label": "🌿 Maximum Lifespan (50%)", "badge": "50% CAP", "desc": "Maximum preservation for continuous AC desk use."},
                {"value": 80, "label": "⚖️ Daily Balance (80%)", "badge": "80% CAP", "desc": "Recommended balance for mobile and desk usage."},
                {"value": 100, "label": "✈️ Full Capacity (100%)", "badge": "100% FULL", "desc": "Full 100% capacity."},
            ],
        }

    # 6. Check for Huawei MateBook (charge_thresholds)
    huawei_candidates = (
        glob.glob("/sys/devices/platform/huawei-wmi/charge_thresholds")
        + glob.glob("/sys/bus/platform/drivers/huawei-wmi/*/charge_thresholds")
        + glob.glob("/sys/bus/platform/devices/huawei-wmi/charge_thresholds")
    )
    huawei_paths = sorted(list(set([os.path.realpath(p) for p in huawei_candidates if os.path.exists(p)])))
    if huawei_paths:
        return {
            "type": "huawei",
            "driver_name": "Huawei MateBook WMI (charge_thresholds)",
            "paths": huawei_paths,
            "supports_slider": False,
            "min_limit": 70,
            "max_limit": 100,
            "step": 10,
            "hardware_note": "Huawei MateBook provides Home (70%), Work (80%), and Travel (100%) modes.",
            "presets": [
                {"value": 70, "label": "🌿 Home Mode (40-70%)", "badge": "HOME", "desc": "Best for prolonged AC charger connection at home."},
                {"value": 80, "label": "⚖️ Work Mode (70-80%)", "badge": "WORK", "desc": "Balanced protection for office and meetings."},
                {"value": 100, "label": "✈️ Travel Mode (95-100%)", "badge": "TRAVEL", "desc": "Full capacity for travel."},
            ],
        }

    return {
        "type": "unsupported",
        "driver_name": "No supported threshold interface detected",
        "paths": [],
        "supports_slider": False,
        "min_limit": 100,
        "max_limit": 100,
        "step": 1,
        "hardware_note": "No hardware battery limit interface was detected on this device.",
        "presets": [],
    }


def can_write_direct(interface_info=None):
    """Returns True if the current user can write to the control files directly (e.g. via udev plugdev rule)."""
    if interface_info is None:
        interface_info = detect_control_interface()
    paths = interface_info.get("paths", [])
    if not paths:
        return False
    return any(os.path.exists(p) and os.access(p, os.W_OK) for p in paths)


def get_current_threshold_and_status(interface_info):
    """Reads the current hardware limit threshold and status description."""
    itype = interface_info.get("type", "unsupported")
    paths = interface_info.get("paths", [])

    if not paths:
        return None, "Not Supported", False

    primary_path = paths[0]
    raw_val = read_file(primary_path)

    if itype == "percentage":
        thresh = read_int(primary_path)
        display = f"{thresh}%" if thresh is not None else "Unknown"
        return thresh, display, False

    elif itype == "conservation_mode":
        is_active = (raw_val == "1")
        thresh = 60 if is_active else 100
        display = "🌿 Conservation Mode (~60%)" if is_active else "✈️ Full Capacity (100%)"
        return thresh, display, is_active

    elif itype == "lg_care":
        is_active = (raw_val == "80")
        thresh = 80 if is_active else 100
        display = "🌿 Battery Care (80%)" if is_active else "✈️ Full Capacity (100%)"
        return thresh, display, is_active

    elif itype == "samsung_extender":
        is_active = (raw_val == "1")
        thresh = 80 if is_active else 100
        display = "🌿 Life Extender (80%)" if is_active else "✈️ Full Capacity (100%)"
        return thresh, display, is_active

    elif itype == "sony_care":
        val = read_int(primary_path)
        thresh = 100 if val == 0 else (val if val else 100)
        display = f"🌿 Battery Care ({thresh}%)" if thresh < 100 else "✈️ Full Capacity (100%)"
        return thresh, display, (thresh < 100)

    elif itype == "huawei":
        display = f"Thresholds: {raw_val}" if raw_val else "Unknown"
        thresh = 80
        if raw_val:
            parts = raw_val.split()
            if len(parts) >= 2 and parts[1].isdigit():
                thresh = int(parts[1])
        return thresh, display, (thresh < 95)

    return None, "Unknown", False


def get_battery_info():
    """Returns a comprehensive dictionary with battery health, laptop model, and charge limit configuration."""
    laptop = get_laptop_info()
    bat_devices = find_battery_devices()
    primary_bat = bat_devices[0] if bat_devices else "/sys/class/power_supply/BAT0"

    capacity = read_int(os.path.join(primary_bat, "capacity"))
    status = read_file(os.path.join(primary_bat, "status")) or "Unknown"
    manufacturer = read_file(os.path.join(primary_bat, "manufacturer")) or "Unknown"
    model = read_file(os.path.join(primary_bat, "model_name")) or "Unknown"
    cycle_count = read_int(os.path.join(primary_bat, "cycle_count"))
    charge_types = read_file(os.path.join(primary_bat, "charge_types"))

    interface = detect_control_interface()
    threshold, threshold_display, is_conservation_active = get_current_threshold_and_status(interface)

    # Check systemd persistence service status
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

    # AC adapter status
    ac_online = None
    base_ps = "/sys/class/power_supply"
    if os.path.exists(base_ps):
        for entry in os.listdir(base_ps):
            p = os.path.join(base_ps, entry)
            dev_type = read_file(os.path.join(p, "type"))
            if dev_type in ("Mains", "AC", "USB") or entry.startswith("AC") or entry.startswith("ADP"):
                online_val = read_file(os.path.join(p, "online"))
                if online_val == "1":
                    ac_online = True
                    break
                elif online_val == "0" and ac_online is None:
                    ac_online = False

    return {
        "laptop": laptop,
        "bat_path": primary_bat,
        "all_batteries": bat_devices,
        "capacity": capacity,
        "status": status,
        "manufacturer": manufacturer,
        "model": model,
        "cycle_count": cycle_count,
        "charge_types": charge_types,
        "interface": interface,
        "threshold": threshold,
        "threshold_display": threshold_display,
        "is_conservation_active": is_conservation_active,
        "service_enabled": service_enabled,
        "ac_online": ac_online,
        "is_root": (os.geteuid() == 0),
        "can_write_direct": can_write_direct(interface),
        "helper_installed": os.path.exists(HELPER_SCRIPT),
    }


def apply_limit_direct(limit):
    """
    Sets battery limit directly in sysfs according to the detected interface.
    Requires write permission on the target sysfs files.
    """
    try:
        limit = int(limit)
        if limit < 20 or limit > 100:
            return False, "Limit must be between 20 and 100"
    except (ValueError, TypeError):
        return False, "Limit must be an integer"

    interface = detect_control_interface()
    itype = interface.get("type", "unsupported")
    paths = interface.get("paths", [])

    if itype == "unsupported" or not paths:
        return False, "No supported battery threshold interface found on this system."

    # Determine string value to write based on interface
    if itype == "percentage":
        write_val = f"{limit}\n"
    elif itype == "conservation_mode":
        write_val = "1\n" if limit <= 80 else "0\n"
    elif itype == "lg_care":
        write_val = "80\n" if limit <= 80 else "100\n"
    elif itype == "samsung_extender":
        write_val = "1\n" if limit <= 80 else "0\n"
    elif itype == "sony_care":
        write_val = "50\n" if limit <= 50 else ("80\n" if limit <= 80 else "0\n")
    elif itype == "huawei":
        if limit <= 70:
            write_val = "40 70\n"
        elif limit <= 80:
            write_val = "70 80\n"
        else:
            write_val = "95 100\n"
    else:
        return False, f"Unknown interface type: {itype}"

    written = []
    for path in paths:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(write_val)
            written.append(path)
        except PermissionError:
            return False, f"Permission denied writing to {path}. Root or plugdev group access required."
        except Exception as e:
            return False, f"Error writing to {path}: {e}"

    # Write systemd service for reboot persistence if root
    if os.geteuid() == 0:
        _write_systemd_service(limit, itype)

    if itype == "conservation_mode":
        state_str = "Enabled (~55-60% capacity cap)" if limit <= 80 else "Disabled (100% full capacity)"
        return True, f"Successfully updated Lenovo Conservation Mode: {state_str}!"
    else:
        return True, f"Successfully set charge limit to {limit}%! ({', '.join(written)})"


def _write_systemd_service(limit, itype=None):
    """Creates and enables systemd service for reboot & resume persistence."""
    conv_val = 1 if limit <= 80 else 0
    lg_val = 80 if limit <= 80 else 100
    sams_val = 1 if limit <= 80 else 0
    sony_val = 50 if limit <= 50 else (80 if limit <= 80 else 0)
    hw_val = "40 70" if limit <= 70 else ("70 80" if limit <= 80 else "95 100")

    exec_cmd = (
        f"/bin/bash -c '"
        f"for f in /sys/class/power_supply/*/charge_control_end_threshold /sys/class/power_supply/*/charge_stop_threshold /sys/class/power_supply/macsmc-battery/charge_control_limit_max; do [ -f \"$f\" ] && echo {limit} > \"$f\" || true; done; "
        f"for f in /sys/bus/platform/drivers/ideapad_acpi/*/conservation_mode /sys/bus/platform/drivers/ideapad_laptop/*/conservation_mode /sys/bus/platform/devices/VPC2004*/conservation_mode /sys/devices/platform/VPC2004*/conservation_mode; do [ -f \"$f\" ] && echo {conv_val} > \"$f\" || true; done; "
        f"for f in /sys/devices/platform/lg-laptop/battery_care_limit /sys/bus/platform/drivers/lg-laptop/*/battery_care_limit; do [ -f \"$f\" ] && echo {lg_val} > \"$f\" || true; done; "
        f"for f in /sys/devices/platform/samsung*/battery_life_extender; do [ -f \"$f\" ] && echo {sams_val} > \"$f\" || true; done; "
        f"for f in /sys/devices/platform/sony-laptop/battery_care_limiter; do [ -f \"$f\" ] && echo {sony_val} > \"$f\" || true; done; "
        f"for f in /sys/devices/platform/huawei-wmi/charge_thresholds; do [ -f \"$f\" ] && echo \"{hw_val}\" > \"$f\" || true; done'"
    )

    service_content = f"""[Unit]
Description=Set battery charge threshold on boot and resume
After=multi-user.target suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target

[Service]
Type=oneshot
ExecStart={exec_cmd}

[Install]
WantedBy=multi-user.target suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target
"""
    try:
        with open(SYSTEMD_SERVICE_PATH, "w", encoding="utf-8") as f:
            f.write(service_content)
        subprocess.run(["systemctl", "daemon-reload"], check=False, capture_output=True)
        subprocess.run(["systemctl", "enable", "battery-manager.service"], check=False, capture_output=True)
        subprocess.run(["systemctl", "start", "battery-manager.service"], check=False, capture_output=True)
    except Exception as e:
        print(f"Warning: Could not configure systemd service: {e}", file=sys.stderr)


def apply_limit(limit):
    """Primary entry point to apply battery limit."""
    return apply_limit_direct(limit)


def print_diagnostic_report():
    """Prints a friendly human-readable diagnostic report."""
    info = get_battery_info()
    laptop = info["laptop"]
    interface = info["interface"]

    print("══════════════════════════════════════════════════════════════")
    print(f" 💻 Laptop Model:  {laptop.get('display_name')}")
    print(f" 🔋 Battery:       {info.get('manufacturer')} {info.get('model')} ({info.get('bat_path')})")
    print(f" 📊 Current Level: {info.get('capacity')}% ({info.get('status')})")
    if info.get("cycle_count"):
        print(f" 🔄 Cycle Count:   {info.get('cycle_count')}")
    print("──────────────────────────────────────────────────────────────")
    print(f" ⚙️ Driver:        {interface.get('driver_name')}")
    print(f" 🏷️ Interface:     {interface.get('type')}")
    print(f" 📁 Sysfs Paths:   {', '.join(interface.get('paths', [])) or 'None'}")
    print(f" 🎯 Current Limit: {info.get('threshold_display')}")
    print(f" ℹ️ Capability:    {interface.get('hardware_note')}")
    print(f" 🔄 Persistence:   {'Enabled (systemd)' if info.get('service_enabled') else 'Not active'}")
    print(f" ✍️ Direct Access: {'Yes (plugdev / root)' if info.get('can_write_direct') or info.get('is_root') else 'Requires pkexec / sudo'}")
    print("══════════════════════════════════════════════════════════════")


def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "info":
            print(json.dumps(get_battery_info(), indent=2))
        elif cmd in ("status", "detect", "report"):
            print_diagnostic_report()
        elif cmd == "set" and len(sys.argv) > 2:
            success, msg = apply_limit(sys.argv[2])
            print(msg)
            sys.exit(0 if success else 1)
        else:
            print("Usage: battery_limiter_backend.py [info | status | set <limit>]")
            sys.exit(1)
    else:
        print(json.dumps(get_battery_info(), indent=2))


if __name__ == "__main__":
    main()
