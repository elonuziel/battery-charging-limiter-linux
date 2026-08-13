#!/usr/bin/env python3
"""
Battery Charge Limiter GUI for Linux (GTK 3).
Helps users choose an optimal charging limit, applies it, and ensures persistence on reboot.
Designed for ASUS laptops on Ubuntu Linux with systemd.
"""

import sys
import os
import subprocess

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

import battery_limiter_backend

HELPER_PATH = "/usr/local/bin/battery-limiter-helper"

CSS_STYLES = b"""
* {
    font-family: "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Open Sans", sans-serif;
}
window.main-window {
    background-color: #181825;
    color: #cdd6f4;
}
.header-title {
    font-size: 21px;
    font-weight: 800;
    color: #cdd6f4;
}
.header-subtitle {
    font-size: 13px;
    color: #a6adc8;
}
.card {
    background-color: #1e1e2e;
    border-radius: 12px;
    padding: 16px;
    border: 1px solid #313244;
}
.card-title {
    font-size: 14px;
    font-weight: 700;
    color: #cdd6f4;
}
.status-value {
    font-size: 28px;
    font-weight: 800;
    color: #89b4fa;
}
.status-label {
    font-size: 11px;
    color: #a6adc8;
}
.badge {
    border-radius: 20px;
    padding: 3px 10px;
    font-weight: 700;
    font-size: 11px;
}
.badge-success { background-color: #1c4a2f; color: #a6e3a1; }
.badge-warning { background-color: #4a3a1c; color: #f9e2af; }
.badge-info    { background-color: #1d3557; color: #89b4fa; }
.badge-error   { background-color: #42202b; color: #f38ba8; }

.preset-card {
    background-color: #1e1e2e;
    border-radius: 12px;
    border: 2px solid #313244;
    padding: 12px;
}
.preset-card:hover {
    border-color: #585b70;
    background-color: #252538;
}
.preset-card-selected {
    border-color: #89b4fa;
    background-color: #18243b;
}
.preset-title {
    font-size: 14px;
    font-weight: 700;
    color: #89b4fa;
}
.preset-subtitle {
    font-size: 11px;
    color: #bac2de;
}
.btn-primary {
    background: linear-gradient(135deg, #89b4fa, #74c7ec);
    color: #11111b;
    font-weight: 700;
    font-size: 14px;
    border-radius: 10px;
    padding: 11px 24px;
    border: none;
}
.btn-primary:hover {
    background: linear-gradient(135deg, #b4befe, #89b4fa);
}
.btn-secondary {
    background-color: #313244;
    color: #cdd6f4;
    font-weight: 600;
    font-size: 12px;
    border-radius: 8px;
    padding: 6px 12px;
    border: none;
}
.btn-secondary:hover { background-color: #45475a; }

.notice-box {
    border-radius: 10px;
    padding: 9px 13px;
    font-size: 12px;
}
.notice-info    { background-color: #1a2a3e; border: 1px solid #2a4060; color: #89b4fa; }
.notice-success { background-color: #1c3a27; border: 1px solid #2e5c3e; color: #a6e3a1; }
.notice-warning { background-color: #3a2e1c; border: 1px solid #5c4a2e; color: #f9e2af; }
.notice-error   { background-color: #42202b; border: 1px solid #6c2e3d; color: #f38ba8; }
"""


def create_desktop_shortcut():
    desktop_dir = os.path.expanduser("~/Desktop")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    gui_script = os.path.join(script_dir, "battery_limiter_gui.py")
    content = (
        "[Desktop Entry]\n"
        "Name=Battery Charge Limiter\n"
        "Comment=Protect laptop battery health by setting custom charge limit thresholds\n"
        f"Exec=/usr/bin/python3 {gui_script}\n"
        "Icon=battery-good-charging\n"
        "Terminal=false\n"
        "Type=Application\n"
        "Categories=Settings;HardwareSettings;System;GTK;\n"
        "Keywords=battery;charge;limit;threshold;asus;laptop;health;\n"
    )
    if os.path.isdir(desktop_dir):
        target = os.path.join(desktop_dir, "battery-limiter.desktop")
        try:
            with open(target, "w") as f:
                f.write(content)
            os.chmod(target, 0o755)
            subprocess.run(["gio", "set", target, "metadata::trusted", "true"],
                           check=False, capture_output=True)
            return True, target
        except Exception as e:
            return False, str(e)
    return False, "Desktop directory not found"


class BatteryLimiterApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="Battery Charge Limiter")
        self.set_default_size(520, 760)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.get_style_context().add_class("main-window")

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS_STYLES)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.selected_target = 80
        self.preset_widgets = {}

        self.build_ui()
        self.refresh_status()
        GLib.timeout_add_seconds(3, self.refresh_status)

    # ── UI construction ──────────────────────────────────────────────────────

    def build_ui(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.add(scroll)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        root.set_margin_top(20)
        root.set_margin_bottom(20)
        root.set_margin_left(22)
        root.set_margin_right(22)
        scroll.add(root)

        # Header
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hdr_txt = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        ttl = Gtk.Label(label="⚡ Battery Charge Limiter", xalign=0)
        ttl.get_style_context().add_class("header-title")
        sub = Gtk.Label(
            label="Extend battery lifespan by capping the max charge percentage",
            xalign=0, wrap=True
        )
        sub.get_style_context().add_class("header-subtitle")
        hdr_txt.pack_start(ttl, False, False, 0)
        hdr_txt.pack_start(sub, False, False, 0)

        shortcut_btn = Gtk.Button(label="📌 Desktop Shortcut")
        shortcut_btn.get_style_context().add_class("btn-secondary")
        shortcut_btn.connect("clicked", lambda _: self._do_desktop_shortcut())

        hdr.pack_start(hdr_txt, True, True, 0)
        hdr.pack_end(shortcut_btn, False, False, 0)
        root.pack_start(hdr, False, False, 0)

        # Auth / install status notice
        self.auth_notice = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.auth_notice.get_style_context().add_class("notice-box")
        self.auth_lbl = Gtk.Label(label="", xalign=0)
        self.auth_lbl.set_line_wrap(True)
        self.auth_notice.pack_start(self.auth_lbl, False, False, 0)
        root.pack_start(self.auth_notice, False, False, 0)

        # Battery status card
        status_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        status_card.get_style_context().add_class("card")

        status_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        status_title = Gtk.Label(label="Live Battery Status", xalign=0)
        status_title.get_style_context().add_class("card-title")
        self.service_badge = Gtk.Label(label="")
        self.service_badge.get_style_context().add_class("badge")
        status_hdr.pack_start(status_title, True, True, 0)
        status_hdr.pack_end(self.service_badge, False, False, 0)
        status_card.pack_start(status_hdr, False, False, 0)

        # Model info
        self.model_lbl = Gtk.Label(label="", xalign=0)
        self.model_lbl.get_style_context().add_class("header-subtitle")
        status_card.pack_start(self.model_lbl, False, False, 0)

        # Stats row
        grid = Gtk.Grid()
        grid.set_column_spacing(20)
        grid.set_row_spacing(4)
        grid.set_column_homogeneous(True)

        def stat_col(title, row=0, col=0):
            lbl = Gtk.Label(label=title, xalign=0)
            lbl.get_style_context().add_class("status-label")
            val = Gtk.Label(label="--", xalign=0)
            val.get_style_context().add_class("status-value")
            grid.attach(lbl, col, row, 1, 1)
            grid.attach(val, col, row + 1, 1, 1)
            return val

        self.cap_lbl = stat_col("Current Level", col=0)
        self.thresh_lbl = stat_col("Hardware Limit", col=1)
        self.status_lbl = stat_col("Power Status", col=2)

        status_card.pack_start(grid, False, False, 0)

        self.level_bar = Gtk.LevelBar()
        self.level_bar.set_min_value(0.0)
        self.level_bar.set_max_value(1.0)
        self.level_bar.set_value(0.0)
        status_card.pack_start(self.level_bar, False, False, 0)

        root.pack_start(status_card, False, False, 0)

        # Preset cards
        choose_lbl = Gtk.Label(label="Choose Your Limit", xalign=0)
        choose_lbl.get_style_context().add_class("card-title")
        root.pack_start(choose_lbl, False, False, 0)

        presets = [
            (60,  "🌿 Maximum Lifespan  (60%)",
             "Ideal for always-plugged-in desks. Minimises voltage stress and heat."),
            (80,  "⚖️ Daily Balance  (80%)",
             "Recommended. Best mix of longevity and enough capacity for mobile use."),
            (100, "✈️ Full Capacity  (100%)",
             "For travel or long off-grid use. Revert to 80% when back at desk."),
        ]
        presets_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for pct, title, desc in presets:
            btn = Gtk.Button()
            btn.get_style_context().add_class("preset-card")
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            t = Gtk.Label(label=title, xalign=0)
            t.get_style_context().add_class("preset-title")
            d = Gtk.Label(label=desc, xalign=0)
            d.get_style_context().add_class("preset-subtitle")
            d.set_line_wrap(True)
            inner.pack_start(t, False, False, 0)
            inner.pack_start(d, False, False, 0)
            btn.add(inner)
            btn.connect("clicked", self._on_preset, pct)
            presets_box.pack_start(btn, False, False, 0)
            self.preset_widgets[pct] = btn
        root.pack_start(presets_box, False, False, 0)

        # Custom slider
        slider_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        slider_card.get_style_context().add_class("card")
        slider_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        slider_title = Gtk.Label(label="Custom Value", xalign=0)
        slider_title.get_style_context().add_class("card-title")
        self.slider_lbl = Gtk.Label(label="80%", xalign=1)
        self.slider_lbl.get_style_context().add_class("preset-title")
        slider_hdr.pack_start(slider_title, True, True, 0)
        slider_hdr.pack_end(self.slider_lbl, False, False, 0)
        slider_card.pack_start(slider_hdr, False, False, 0)
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 20, 100, 5)
        self.scale.set_value(80)
        self.scale.set_draw_value(False)
        self.scale.connect("value-changed", self._on_scale)
        slider_card.pack_start(self.scale, False, False, 0)
        root.pack_start(slider_card, False, False, 0)

        # Apply button
        self.apply_btn = Gtk.Button(label="Apply Limit & Save (Persists on Reboot)")
        self.apply_btn.get_style_context().add_class("btn-primary")
        self.apply_btn.connect("clicked", self._on_apply)
        root.pack_start(self.apply_btn, False, False, 0)

        # Result notice
        self.result_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.result_box.get_style_context().add_class("notice-box")
        self.result_lbl = Gtk.Label(label="", xalign=0)
        self.result_lbl.set_line_wrap(True)
        self.result_box.pack_start(self.result_lbl, False, False, 0)
        self.result_box.set_no_show_all(True)
        self.result_box.hide()
        root.pack_start(self.result_box, False, False, 0)

        self._update_selection(80)

    # ── Status refresh ────────────────────────────────────────────────────────

    def refresh_status(self):
        info = battery_limiter_backend.get_battery_info()
        cap = info.get("capacity")
        thresh = info.get("threshold")
        stat = info.get("status", "Unknown")
        svc = info.get("service_enabled", False)
        manufacturer = info.get("manufacturer", "")
        model = info.get("model", "")
        can_write = info.get("can_write_direct", False)
        helper_ok = info.get("helper_installed", False)
        is_root = info.get("is_root", False)

        # Model label
        self.model_lbl.set_text(f"{manufacturer} {model}".strip())

        # Stats
        self.cap_lbl.set_text(f"{cap}%" if cap is not None else "N/A")
        self.thresh_lbl.set_text(f"{thresh}%" if thresh is not None else "N/A")
        self.status_lbl.set_text(stat)
        if cap is not None:
            self.level_bar.set_value(cap / 100.0)

        # Persistence badge
        ctx = self.service_badge.get_style_context()
        for cls in ["badge-success", "badge-info", "badge-warning"]:
            ctx.remove_class(cls)
        if svc:
            self.service_badge.set_text("✓ Persists on Reboot")
            ctx.add_class("badge-success")
        else:
            self.service_badge.set_text("No Boot Persistence")
            ctx.add_class("badge-warning")

        # Auth notice
        ctx2 = self.auth_notice.get_style_context()
        for cls in ["notice-info", "notice-success", "notice-warning", "notice-error"]:
            ctx2.remove_class(cls)
        if is_root or can_write:
            ctx2.add_class("notice-success")
            self.auth_lbl.set_text(
                "✅ Ready: Direct sysfs write access confirmed. Limits apply immediately without a password."
            )
        elif helper_ok:
            ctx2.add_class("notice-info")
            self.auth_lbl.set_text(
                "🔑 Helper installed: A graphical password prompt will appear when you apply a limit."
            )
        else:
            ctx2.add_class("notice-warning")
            self.auth_lbl.set_text(
                "⚠️ Not yet installed. Run:  sudo ./install.sh\n"
                "This sets up a udev rule for passwordless control + the polkit helper."
            )

        return True  # keep timeout running

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_preset(self, _btn, pct):
        self.scale.set_value(pct)
        self._update_selection(pct)

    def _on_scale(self, scale):
        val = int(scale.get_value())
        self.selected_target = val
        self.slider_lbl.set_text(f"{val}%")
        self._update_selection(val)

    def _update_selection(self, val):
        self.selected_target = val
        self.slider_lbl.set_text(f"{val}%")
        for pct, btn in self.preset_widgets.items():
            ctx = btn.get_style_context()
            if pct == val:
                ctx.add_class("preset-card-selected")
            else:
                ctx.remove_class("preset-card-selected")

    def _do_desktop_shortcut(self):
        ok, path = create_desktop_shortcut()
        if ok:
            self._show_result(f"Desktop shortcut created: {path}", True)
        else:
            self._show_result(f"Could not create shortcut: {path}", False)

    def _on_apply(self, _btn):
        target = self.selected_target
        self.apply_btn.set_sensitive(False)
        self.apply_btn.set_label("Applying…")

        success, msg = self._apply_limit(target)
        self._show_result(msg, success)

        self.apply_btn.set_sensitive(True)
        self.apply_btn.set_label("Apply Limit & Save (Persists on Reboot)")
        GLib.timeout_add(800, self.refresh_status)

    def _apply_limit(self, target):
        """Try all available auth strategies in order."""
        info = battery_limiter_backend.get_battery_info()

        # 1. Direct write (root or udev plugdev rule active)
        if info.get("is_root") or info.get("can_write_direct"):
            return battery_limiter_backend.apply_limit(target)

        # 2. Shell helper via pkexec (most reliable with polkit GUI dialog)
        if info.get("helper_installed"):
            return self._try_pkexec_helper(target)

        # 3. pkexec python backend (fallback, may fail on some systems)
        result = self._try_pkexec_python(target)
        if result[0]:
            return result

        # 4. Open terminal with sudo as last resort
        return self._try_terminal_sudo(target)

    def _try_pkexec_helper(self, target):
        try:
            res = subprocess.run(
                ["pkexec", HELPER_PATH, "set", str(target)],
                capture_output=True, text=True, timeout=30
            )
            if res.returncode == 0:
                return True, res.stdout.strip() or f"Limit set to {target}%!"
            if res.returncode == 126:
                return False, "Authentication cancelled."
            return False, f"Helper failed: {res.stderr.strip() or res.stdout.strip()}"
        except subprocess.TimeoutExpired:
            return False, "Authentication timed out."
        except Exception as e:
            return False, f"pkexec error: {e}"

    def _try_pkexec_python(self, target):
        backend_script = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "battery_limiter_backend.py")
        )
        python3 = "/usr/bin/python3"
        try:
            res = subprocess.run(
                ["pkexec", python3, backend_script, "set", str(target)],
                capture_output=True, text=True, timeout=30
            )
            if res.returncode == 0:
                return True, res.stdout.strip() or f"Limit set to {target}%!"
        except Exception:
            pass
        return False, ""

    def _try_terminal_sudo(self, target):
        backend_script = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "battery_limiter_backend.py")
        )
        cmd = (
            f"sudo /usr/bin/python3 {backend_script} set {target} "
            f"&& echo 'Done! You can close this window.' "
            f"|| echo 'ERROR - see message above.'; read"
        )
        try:
            subprocess.Popen(["x-terminal-emulator", "-e", f"bash -c '{cmd}'"])
            return True, (
                f"Opened a terminal — please enter your password to apply {target}% limit. "
                f"The app will update in a few seconds."
            )
        except Exception as e:
            return False, (
                f"Could not open terminal: {e}\n"
                f"Run manually:  sudo ./limitd.sh {target}"
            )

    def _show_result(self, msg, success):
        self.result_lbl.set_text(msg)
        ctx = self.result_box.get_style_context()
        for cls in ["notice-success", "notice-error", "notice-warning", "notice-info"]:
            ctx.remove_class(cls)
        ctx.add_class("notice-success" if success else "notice-error")
        self.result_box.show_all()


def main():
    app = BatteryLimiterApp()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
