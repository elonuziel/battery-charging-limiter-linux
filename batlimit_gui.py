#!/usr/bin/env python3
"""Battery Charging Limiter GUI

A simple Tkinter desktop app that wraps the existing shell scripts to set
battery charge thresholds and optionally persist settings across reboots.

Requirements:
  - Python 3.6+ with tkinter (python3-tk)
  - pkexec (polkit) – preferred for GUI privilege elevation
    OR sudo available in PATH (requires a terminal-capable sudo or sudoers NOPASSWD)
  - The shell scripts (limit.sh, limitd.sh, limit_runit.sh, limitrc.sh) must
    be in the same directory as this file.

Usage:
  python3 batlimit_gui.py
"""

import glob
import os
import re
import shutil
import subprocess
import tkinter as tk
from tkinter import ttk

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

SYSFS_GLOB = "/sys/class/power_supply/BAT*/charge_control_end_threshold"

# Map init-system name → persistence script filename
PERSIST_SCRIPTS = {
    "systemd": "limitd.sh",
    "runit":   "limit_runit.sh",
    "openrc":  "limitrc.sh",
}

ONESHOT_SCRIPT = "limit.sh"

# pkexec exit codes
PKEXEC_DISMISSED = 126
PKEXEC_NOT_AUTHORIZED = 127

# ---------------------------------------------------------------------------
# System detection helpers
# ---------------------------------------------------------------------------


def find_threshold_path():
    """Return the first matching sysfs charge_control_end_threshold path, or None."""
    matches = glob.glob(SYSFS_GLOB)
    return matches[0] if matches else None


def read_current_limit(path):
    """Read the current threshold value from *path*.  Returns a string or None."""
    try:
        with open(path) as fh:
            return fh.read().strip()
    except OSError:
        return None


def detect_init():
    """Detect the running init system.

    Returns one of: 'systemd', 'runit', 'openrc', or 'unknown'.
    """
    # Primary: read /proc/1/comm
    try:
        with open("/proc/1/comm") as fh:
            comm = fh.read().strip()
        if comm == "systemd":
            return "systemd"
        if comm == "runit":
            return "runit"
        if comm in ("openrc-init", "openrc"):
            return "openrc"
    except OSError:
        pass

    # Fallback: look for characteristic paths / executables
    if os.path.isdir("/run/systemd/private") or shutil.which("systemctl"):
        return "systemd"
    if os.path.isdir("/run/runit") or shutil.which("runit"):
        return "runit"
    if shutil.which("rc-service") or shutil.which("openrc"):
        return "openrc"

    return "unknown"


def get_privilege_prefix():
    """Return the privilege-escalation command prefix as a list.

    Prefers pkexec (works without a terminal in GUI contexts).
    Falls back to sudo (requires a terminal or NOPASSWD sudoers entry).
    """
    if shutil.which("pkexec"):
        return ["pkexec"]
    return ["sudo"]


def strip_ansi(text):
    """Remove ANSI escape sequences from *text*."""
    return re.sub(r"\x1b\[[0-9;]*[mK]", "", text)


# ---------------------------------------------------------------------------
# Script execution
# ---------------------------------------------------------------------------


def run_script(script_name, value):
    """Run *script_name* with *value* as the sole argument, elevated.

    Returns a tuple (success: bool, message: str).
    """
    script_path = os.path.join(SCRIPT_DIR, script_name)
    if not os.path.isfile(script_path):
        return False, f"Script not found: {script_path}"

    priv = get_privilege_prefix()
    cmd = priv + ["bash", script_path, str(value)]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return False, "Command timed out after 60 seconds."
    except FileNotFoundError as exc:
        return False, f"Executable not found: {exc}"

    output = strip_ansi((result.stdout + result.stderr).strip())

    if result.returncode == 0:
        return True, output or f"Limit set to {value}%."
    if result.returncode == PKEXEC_DISMISSED:
        return False, "Authorization cancelled."
    if result.returncode == PKEXEC_NOT_AUTHORIZED:
        return False, "Authentication failed."

    msg = output or f"Script exited with code {result.returncode}."
    return False, f"Error: {msg}"


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------


class BatlimitApp(tk.Tk):
    """Single-window Tkinter application for the battery charging limiter."""

    def __init__(self):
        super().__init__()
        self.title("Battery Charging Limiter")
        self.resizable(False, False)

        # Configure custom styles
        self._setup_styles()

        # Detect system capabilities at startup
        self.threshold_path = find_threshold_path()
        self.init_system = detect_init()

        self._build_ui()
        self._refresh_current()

    def _setup_styles(self):
        """Configure custom ttk styles for better visual polish."""
        style = ttk.Style()
        style.theme_use("clam")

        # Configure label frame style
        style.configure(
            "TLabelframe.Label",
            font=("TkDefaultFont", 10, "bold"),
        )

        # Configure button style
        style.configure(
            "Apply.TButton",
            font=("TkDefaultFont", 11, "bold"),
            padding=12,
        )

        # Configure checkbox style
        style.configure(
            "Persist.TCheckbutton",
            font=("TkDefaultFont", 12, "bold"),
            padding=12,
        )

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Configure main window padding
        main_pad = 16

        # ── Title ─────────────────────────────────────────────────────
        title_label = ttk.Label(
            self,
            text="Battery Charging Limiter",
            font=("TkDefaultFont", 14, "bold"),
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(main_pad, 8), padx=main_pad)

        # ── System info ───────────────────────────────────────────────
        info_frame = ttk.LabelFrame(self, text="System Info", padding=10)
        info_frame.grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=main_pad, pady=8
        )
        info_frame.columnconfigure(1, weight=1)

        bat_label = self.threshold_path or "Not found – charging threshold unsupported on this machine"
        bat_color = "green" if self.threshold_path else "red"

        ttk.Label(info_frame, text="Battery path:", font=("TkDefaultFont", 9, "bold")).grid(
            row=0, column=0, sticky="w", pady=5
        )
        ttk.Label(info_frame, text=bat_label, foreground=bat_color).grid(
            row=0, column=1, sticky="w", padx=(8, 0), pady=5
        )

        ttk.Label(info_frame, text="Init system:", font=("TkDefaultFont", 9, "bold")).grid(
            row=1, column=0, sticky="w", pady=5
        )
        ttk.Label(info_frame, text=self.init_system).grid(
            row=1, column=1, sticky="w", padx=(8, 0), pady=5
        )

        persist_script = PERSIST_SCRIPTS.get(self.init_system)
        persist_available = persist_script is not None and os.path.isfile(
            os.path.join(SCRIPT_DIR, persist_script)
        )
        persist_info = persist_script if persist_available else "not supported"
        persist_color = "green" if persist_available else "gray"

        ttk.Label(info_frame, text="Persist script:", font=("TkDefaultFont", 9, "bold")).grid(
            row=2, column=0, sticky="w", pady=5
        )
        ttk.Label(info_frame, text=persist_info, foreground=persist_color).grid(
            row=2, column=1, sticky="w", padx=(8, 0), pady=5
        )

        # ── Separator ─────────────────────────────────────────────────
        ttk.Separator(self, orient="horizontal").grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=main_pad, pady=8
        )

        # ── Current limit ─────────────────────────────────────────────
        ttk.Label(self, text="Current limit:", font=("TkDefaultFont", 10, "bold")).grid(
            row=3, column=0, sticky="w", padx=main_pad, pady=(8, 2)
        )
        self._current_var = tk.StringVar(value="—")
        ttk.Label(
            self, textvariable=self._current_var, font=("TkDefaultFont", 16, "bold"), foreground="#2E7D32"
        ).grid(row=3, column=1, sticky="w", padx=main_pad, pady=(8, 2))

        # ── New value spinbox ──────────────────────────────────────────
        ttk.Label(self, text="New limit (%):", font=("TkDefaultFont", 10, "bold")).grid(
            row=4, column=0, sticky="w", padx=main_pad, pady=(8, 2)
        )
        self._spin_var = tk.StringVar(value="80")
        self._spinbox = ttk.Spinbox(
            self,
            from_=1,
            to=100,
            textvariable=self._spin_var,
            width=10,
            font=("TkDefaultFont", 14, "bold"),
            justify="center",
        )
        self._spinbox.grid(row=4, column=1, sticky="w", padx=main_pad, pady=(8, 2))

        # ── Persist checkbox ───────────────────────────────────────────
        self._persist_var = tk.BooleanVar(value=False)
        cb_text = "Persist on reboot"
        if not persist_available:
            cb_text += f" (unavailable – {self.init_system} not supported)"
        self._persist_cb = ttk.Checkbutton(
            self,
            text=cb_text,
            variable=self._persist_var,
            style="Persist.TCheckbutton",
        )
        if not persist_available:
            self._persist_var.set(False)
            self._persist_cb.state(["disabled"])
        self._persist_cb.grid(
            row=5, column=0, columnspan=2, sticky="w", padx=main_pad, pady=(16, 12)
        )

        # ── Apply button ───────────────────────────────────────────────
        self._apply_btn = ttk.Button(
            self, text="Apply", command=self._on_apply, style="Apply.TButton"
        )
        if not self.threshold_path:
            self._apply_btn.state(["disabled"])
        self._apply_btn.grid(row=6, column=0, columnspan=2, pady=12, sticky="ew", padx=main_pad)

        # ── Status bar ─────────────────────────────────────────────────
        self._status_var = tk.StringVar(value="Ready.")
        self._status_label = ttk.Label(
            self,
            textvariable=self._status_var,
            foreground="gray",
            wraplength=380,
            justify="left",
            font=("TkDefaultFont", 9),
        )
        self._status_label.grid(
            row=7, column=0, columnspan=2, sticky="ew", padx=main_pad, pady=(0, main_pad)
        )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _refresh_current(self):
        if self.threshold_path:
            val = read_current_limit(self.threshold_path)
            self._current_var.set(f"{val}%" if val else "Unknown")
        else:
            self._current_var.set("N/A")

    def _set_status(self, msg, color="gray"):
        self._status_var.set(msg)
        self._status_label.configure(foreground=color)

    def _on_apply(self):
        # Validate input
        try:
            value = int(self._spin_var.get())
        except ValueError:
            self._set_status("Error: enter a whole number between 1 and 100.", "red")
            return

        if not 1 <= value <= 100:
            self._set_status("Error: value must be between 1 and 100.", "red")
            return

        persist = self._persist_var.get()
        if persist:
            script = PERSIST_SCRIPTS.get(self.init_system, ONESHOT_SCRIPT)
        else:
            script = ONESHOT_SCRIPT

        self._set_status(f"Applying {value}% via {script} …")
        self._apply_btn.state(["disabled"])
        self.update_idletasks()

        try:
            success, message = run_script(script, value)
        finally:
            self._apply_btn.state(["!disabled"])

        if success:
            self._refresh_current()
            persist_note = " (will persist on reboot)" if persist else ""
            self._set_status(f"Done – limit set to {value}%{persist_note}.", "green")
        else:
            self._set_status(message, "red")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    app = BatlimitApp()
    app.mainloop()


if __name__ == "__main__":
    main()
