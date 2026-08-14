# Battery Charging Limiter for Linux ⚡

A modern, universal Linux application (GUI & CLI) to control battery charging limit thresholds (e.g., 60%, 80%, or 100%) and prolong laptop battery lifespan. Features automatic hardware detection and **reboot & suspend persistence** via systemd, OpenRC, or Runit.

---

## 🌟 Why Limit Battery Charging?

When a laptop is continuously plugged into AC power, keeping the lithium-ion battery at 100% capacity accelerates chemical degradation due to high voltage stress and thermal build-up.

Limiting the maximum charge threshold significantly extends total battery health and longevity:
- 🌿 **60% (Maximum Lifespan)**: Ideal if your laptop is continuously connected to a charger at a desk or office. Minimizes cell stress.
- ⚖️ **80% (Daily Balance - Recommended)**: Best balance between long battery cycle lifespan and sufficient mobile unplugged capacity.
- ✈️ **100% (Full Capacity)**: For travel, long flights, or extended off-grid work.

---

## 💻 Compatibility & Supported Hardware

This tool features **automatic hardware detection** across major laptop manufacturers on Linux Kernel 5.4+:

| Manufacturer & Series | Driver Interface | Threshold Modes |
| :--- | :--- | :--- |
| **Lenovo ThinkBook, IdeaPad, Yoga, Legion, Xiaoxin** | `ideapad_laptop` (`conservation_mode`) | 🌿 Conservation Mode (~60-80%) / ✈️ Full (100%) |
| **Lenovo ThinkPad** | `thinkpad_acpi` (`charge_control_end_threshold`) | 20% - 100% granular / presets (60%, 80%, 100%) |
| **ASUS ROG, TUF, ZenBook, VivoBook** | `asus_wmi` (`charge_control_end_threshold`) | 20% - 100% granular / presets (60%, 80%, 100%) |
| **Dell Laptops** | `dell-laptop` / ACPI battery sysfs | 20% - 100% granular / presets |
| **LG Gram** | `lg_laptop` (`battery_care_limit`) | 80% / 100% |
| **Samsung Laptops / Galaxy Book** | `samsung_laptop` (`battery_life_extender`) | 80% / 100% |
| **Huawei MateBook** | `huawei_wmi` (`charge_thresholds`) | Home (70%) / Work (80%) / Travel (100%) |
| **Sony Vaio** | `sony_laptop` (`battery_care_limiter`) | 50% / 80% / 100% |
| **Framework, System76, MSI, Apple Silicon (Asahi)** | Standard sysfs `power_supply` nodes | 20% - 100% granular / presets |

---

## 🚀 Quick Start & Installation

### 1. One-Step Installer

Run the installer with `sudo` to configure udev rules (enables passwordless control for `plugdev` users), polkit policies, systemd services, and desktop shortcuts:

```bash
chmod +x install.sh
sudo ./install.sh
```

### 2. Launching the Graphical App (GUI)

Launch **Battery Charge Limiter** from your application menu or run directly:

```bash
python3 battery_limiter_gui.py
```

#### GUI Features:
- 🔍 **Live Hardware Detection**: Displays your laptop model (e.g., *Lenovo ThinkBook 15 G2 ITL*), battery model, and active kernel driver interface.
- 📊 **Real-Time Battery Stats**: Live battery percentage, charging state, AC power connection, and cycle count.
- 🎛️ **Adaptive Control Cards**: Automatically tailors controls to your hardware (presets for Lenovo Conservation Mode vs. granular sliders for ASUS/ThinkPad/Dell).
- 🔄 **Reboot Persistence**: Automatically sets up systemd service so your chosen limit survives reboots, sleep, and hibernations.
- 📌 **One-Click Desktop Icon**: Add a shortcut to your desktop with one click.

---

## 🛠️ Command Line Interface (CLI)

You can inspect hardware and configure thresholds directly from the terminal without launching the GUI.

### 🔍 Diagnostic Status Report
```bash
./battery_limiter_backend.py status
```
*Output example:*
```text
══════════════════════════════════════════════════════════════
 💻 Laptop Model:  LENOVO ThinkBook 15 G2 ITL (20VE)
 🔋 Battery:       Celxpert L19C3PDA (/sys/class/power_supply/BAT1)
 📊 Current Level: 80% (Discharging)
 🔄 Cycle Count:   180
──────────────────────────────────────────────────────────────
 ⚙️ Driver:        Lenovo IdeaPad ACPI (conservation_mode)
 🏷️ Interface:     conservation_mode
 📁 Sysfs Paths:   /sys/devices/.../VPC2004:00/conservation_mode
 🎯 Current Limit: Conservation Mode (~60-80%)
 🔄 Persistence:   Enabled (systemd)
 ✍️ Direct Access: Yes (plugdev / root)
══════════════════════════════════════════════════════════════
```

### 📋 JSON Battery Info
```bash
./battery_limiter_backend.py info
```

### ⚙️ Set Threshold & Enable Reboot Persistence
To set limit to 80% (persists on reboots, suspend, and hibernate):
```bash
sudo ./battery_limiter_backend.py set 80
```

### 📜 Alternative Init Systems
- **Systemd**: `sudo ./limitd.sh 80`
- **OpenRC**: `sudo ./limitrc.sh 80`
- **Runit**: `sudo ./limit_runit.sh 80`

---

## ⚙️ How It Works

1. **Kernel Driver Abstraction**:
   - Modern Linux kernels expose battery charging controls via sysfs attributes under `/sys/class/power_supply/BAT*/` (e.g. `charge_control_end_threshold`), `/sys/bus/platform/drivers/ideapad_acpi/*/conservation_mode`, `/sys/devices/platform/lg-laptop/battery_care_limit`, etc.
2. **Dynamic Limit Application**:
   - When you select a limit (e.g. 80%), the backend writes the appropriate value to the active hardware sysfs interface.
3. **Persistence Across Boots & Suspend**:
   - A lightweight `oneshot` systemd service (`/etc/systemd/system/battery-manager.service`) is created and enabled, restoring your threshold after boot, sleep, hibernate, and suspend.
4. **Passwordless Access via udev**:
   - The installer installs `/etc/udev/rules.d/85-battery-charge-limiter.rules`, granting users in the `plugdev` group direct write access so you can change limits anytime without a password prompt.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
