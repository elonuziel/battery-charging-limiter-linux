# Battery Charging Limiter for Linux (ASUS & Supported Laptops)

A simple yet elegant Linux application (GUI & CLI) to control battery charging limit thresholds (e.g. 60%, 80%, or 100%) and prolong laptop battery lifespan. Supports **reboot persistence** via systemd.

![Battery Charge Limiter GUI](battery-limiter.desktop)

---

## 🌟 Why Limit Battery Charging?

When a laptop is continuously plugged into AC power, keeping the battery at 100% capacity accelerates chemical degradation due to high voltage stress and thermal build-up. 

Limiting the maximum charge threshold extends total battery health and longevity:
- 🌿 **60% (Maximum Lifespan)**: Ideal if your laptop is continuously connected to a charger at a desk or office.
- ⚖️ **80% (Daily Balance - Recommended)**: Best balance between long battery life and mobile usage time.
- ✈️ **100% (Full Capacity)**: For travel, long flights, or extended off-grid work.

---

## 🚀 Quick Start & Installation

### 1. Graphical App (GUI)
Run the simple installer to set executable permissions and add **Battery Charge Limiter** to your application menu:

```bash
chmod +x install.sh
./install.sh
```

You can launch it from your desktop app menu or run directly:
```bash
python3 battery_limiter_gui.py
```

Features:
- Live battery level, charging status, and active limit display
- Visual recommendation cards (60%, 80%, 100%) and fine slider control
- Graphical password prompt (via `pkexec`) to set thresholds and enable systemd persistence automatically

---

### 2. Command Line (CLI) & Persistence

#### Check Current Status
```bash
./battery_limiter_backend.py info
```

#### Set Threshold & Persist on Reboot
To set limit to 80% (persisted on system reboots, sleep, and hibernate):
```bash
sudo ./battery_limiter_backend.py set 80
```

Or using legacy scripts:
- `./limitd.sh 80` (Systemd persistence)
- `./limit_runit.sh 80` (Runit persistence)
- `./limitrc.sh 80` (OpenRC persistence)

---

## ⚙️ How It Works

Modern Linux kernels (5.4+) expose battery charge thresholds via sysfs:
`/sys/class/power_supply/BAT0/charge_control_end_threshold`

When you apply a limit in the app or CLI:
1. Writes the selected percentage to `charge_control_end_threshold`.
2. Creates and enables `/etc/systemd/system/battery-manager.service` so your choice is automatically restored after reboot or system suspend.

---

## 📋 Compatibility

Tested and verified on Linux systems supporting sysfs battery thresholds:
- Asus Vivobook / Zenbook / ROG / TUF Gaming series
- Lenovo ThinkPad series
- Systems running Linux Kernel 5.4+ with systemd, runit, or openrc
