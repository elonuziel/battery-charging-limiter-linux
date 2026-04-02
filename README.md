# Battery Charging limiter Linux (ASUS Laptops)

When the laptop is being constantly used with a charger plugged in it is better to limit the charging at 60% to 80% to improve the battery health.
Many laptop vendors like Asus provide software utility to set the battery max charge threshold but it works only in windows.

With Linux kernel 5.4 added the ability to set a battery charge threshold for many Asus laptops this script uses it to set the limit.

## Usage
Run the script limit.sh with max battery threshold as an argument

`eg: ./limit.sh 60`

*prompt to enter the password since it needs sudo permission*

Will set the battery threshold to 60% so even if the laptop is plugged in it won't charge beyond 60% helps to protect the battery health.

*Note: limit.sh set limit won't persist on system reboot*

or 

For operating systems with systemd use other script limitd.sh that will create a systemd service to apply the limit on system reboot.

`eg: ./limitd.sh 60`

*limitd.sh set limit will persist on system reboot*

Or if you use Runit instead of systemd, use limit_runit.sh

`eg: ./limit_runit.sh 60`

Reboot the system and check if limit works

#### Renable full capacity 

Run the limit.sh script with 100%

`./limit.sh 100`

or

`./limitd.sh 100 `

This will persist the change on reboot if systemd is available

Or use 'limit_runit.sh' for Runit.

`./limit_runit.sh 100`

Note: make the scripts executable before running by executing 
`eg: chmod +x limit.sh`


## GUI (graphical interface)

`batlimit_gui.py` is a Python Tkinter desktop app that wraps the existing shell
scripts and lets you set the battery charge threshold with a point-and-click
interface.

### Requirements

| Requirement | Notes |
|---|---|
| Python 3.6+ with `tkinter` | Install `python3-tk` on Debian/Ubuntu/Mint; usually included on Fedora/Artix/Void |
| `pkexec` (polkit) | **Preferred** – allows privilege elevation without a terminal. Install `polkit`. |
| `sudo` | Fallback if `pkexec` is not found. Requires a terminal-capable session or a `NOPASSWD` sudoers entry for the scripts. |
| Shell scripts | `limit.sh`, `limitd.sh`, `limit_runit.sh`, `limitrc.sh` must be in the same directory as `batlimit_gui.py`. |

### Usage

```bash
python3 batlimit_gui.py
```

The window shows:

* **System Info** – detected battery sysfs path, running init system, and
  which persistence script will be used.
* **Current limit** – the value currently written to the sysfs threshold file.
* **New limit (%)** – a spinbox (1–100) to enter the desired threshold.
* **Persist on reboot** – when checked the appropriate script for your init
  system (`limitd.sh` for systemd, `limit_runit.sh` for runit, `limitrc.sh`
  for OpenRC) is used; otherwise only `limit.sh` is called (one-shot, lost on
  reboot). The checkbox is disabled automatically when no supported init system
  is detected.
* **Apply** – runs the selected script with elevated privileges (via `pkexec`
  or `sudo`). A status message below the button reports success or any error
  (including a cancelled auth dialog).

### Privilege behaviour

The GUI always runs the shell scripts with elevated privileges:

* When `pkexec` is available a polkit authentication dialog is shown – this is
  the recommended flow for desktop use.
* When only `sudo` is available the terminal that launched the GUI is used for
  the password prompt.  If no terminal is attached the command will fail; in
  that case add a `NOPASSWD` sudoers entry for the scripts or install `polkit`.

### Examples

**Set an 80 % one-time limit** (lost on reboot):  
Open the GUI, enter `80` in the spinbox, leave *Persist on reboot* unchecked,
click **Apply**.

**Set a 60 % limit that survives reboot** (systemd system):  
Open the GUI, enter `60`, check *Persist on reboot*, click **Apply**.  The GUI
runs `limitd.sh 60`, which creates and enables a `battery-manager.service`
systemd unit.

---

## More info
* [ASUS Battery Information Center](https://www.asus.com/support/FAQ/1038475/)
* [Arch Wiki](https://wiki.archlinux.org/index.php/Laptop/ASUS#Battery_charge_threshold)


-----
>Tested with :
> - Asus vivobook 15 with AMD Ryzen 3500U running Linux mint 20 (Kernel: 5.8.0-25-generic);
> - Asus Vivobook 15 PRO OLED Ryzen5900 M3500 using artix-linux (Kernel: 5.3.1);
> - Asus TUF Gaming F15 using Debian 12;
> - Asus ExpertBook B5 OLED B5302CEA using Fedora (Workstation Edition) 39 (Kernel: Linux 6.6.9-200.fc39.x86_64);
