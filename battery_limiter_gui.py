#!/usr/bin/env python3
"""
Battery Charge Limiter GUI for Linux (GTK 3).
Helps users choose an optimal charging limit, applies it, and ensures persistence on reboot.
"""

import sys
import os
import subprocess
import json
import time

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

import battery_limiter_backend

CSS_STYLES = b"""
* {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Open Sans", sans-serif;
}

window.main-window {
    background-color: #181825;
    color: #cdd6f4;
}

.header-title {
    font-size: 22px;
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
    font-size: 15px;
    font-weight: 700;
    color: #cdd6f4;
}

.status-value {
    font-size: 32px;
    font-weight: 800;
    color: #89b4fa;
}

.badge {
    border-radius: 20px;
    padding: 4px 12px;
    font-weight: 700;
    font-size: 12px;
}

.badge-success {
    background-color: #264653;
    color: #a6e3a1;
}

.badge-info {
    background-color: #1d3557;
    color: #89b4fa;
}

.preset-card {
    background-color: #1e1e2e;
    border-radius: 12px;
    border: 2px solid #313244;
    padding: 14px;
    transition: all 200ms ease;
}

.preset-card:hover {
    border-color: #89b4fa;
    background-color: #252538;
}

.preset-card-selected {
    border-color: #89b4fa;
    background-color: #18243b;
}

.preset-title {
    font-size: 16px;
    font-weight: 700;
    color: #89b4fa;
}

.preset-subtitle {
    font-size: 12px;
    color: #bac2de;
}

.btn-primary {
    background: linear-gradient(135deg, #89b4fa, #74c7ec);
    color: #11111b;
    font-weight: 700;
    font-size: 15px;
    border-radius: 10px;
    padding: 12px 24px;
    border: none;
    box-shadow: 0 4px 12px rgba(137, 180, 250, 0.25);
}

.btn-primary:hover {
    background: linear-gradient(135deg, #b4befe, #89b4fa);
}

.btn-secondary {
    background-color: #313244;
    color: #cdd6f4;
    font-weight: 600;
    font-size: 13px;
    border-radius: 8px;
    padding: 6px 14px;
    border: none;
}

.btn-secondary:hover {
    background-color: #45475a;
}

.info-note {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 12px;
    color: #94a3b8;
}

.notification-box {
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 13px;
}

.notification-success {
    background-color: #1c3a27;
    color: #a6e3a1;
    border: 1px solid #2e5c3e;
}

.notification-error {
    background-color: #42202b;
    color: #f38ba8;
    border: 1px solid #6c2e3d;
}
"""

def create_desktop_shortcut():
    """Creates a launcher shortcut on the user's Desktop directory."""
    home = os.path.expanduser("~")
    desktop_dir = os.path.join(home, "Desktop")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    gui_script = os.path.join(script_dir, "battery_limiter_gui.py")

    content = f"""[Desktop Entry]
Name=Battery Charge Limiter
Comment=Protect laptop battery health by setting custom charge limit thresholds
Exec=/usr/bin/env python3 {gui_script}
Icon=battery-good-charging
Terminal=false
Type=Application
Categories=Settings;HardwareSettings;System;GTK;
Keywords=battery;charge;limit;threshold;asus;laptop;health;
"""
    if os.path.exists(desktop_dir):
        target_path = os.path.join(desktop_dir, "battery-limiter.desktop")
        try:
            with open(target_path, "w") as f:
                f.write(content)
            os.chmod(target_path, 0o755)
            subprocess.run(["gio", "set", target_path, "metadata::trusted", "true"], check=False)
            return True, target_path
        except Exception as e:
            return False, str(e)
    return False, "Desktop directory not found"

class BatteryLimiterApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="Battery Charge Limiter")
        self.set_default_size(540, 760)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.get_style_context().add_class("main-window")

        # Load Custom CSS
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS_STYLES)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.selected_target = 80
        self.preset_widgets = {}

        self.build_ui()
        self.refresh_status()

        # Auto refresh status every 3 seconds
        GLib.timeout_add_seconds(3, self.refresh_status)

    def build_ui(self):
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_vbox.set_margin_top(20)
        main_vbox.set_margin_bottom(20)
        main_vbox.set_margin_left(24)
        main_vbox.set_margin_right(24)
        self.add(main_vbox)

        # 1. Header with Desktop Shortcut Button
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        header_text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title_lbl = Gtk.Label(label="⚡ Battery Charge Limiter", xalign=0)
        title_lbl.get_style_context().add_class("header-title")
        subtitle_lbl = Gtk.Label(
            label="Extend laptop battery lifespan by setting a max charge threshold",
            xalign=0
        )
        subtitle_lbl.get_style_context().add_class("header-subtitle")
        header_text_box.pack_start(title_lbl, False, False, 0)
        header_text_box.pack_start(subtitle_lbl, False, False, 0)

        shortcut_btn = Gtk.Button(label="📌 Desktop Shortcut")
        shortcut_btn.get_style_context().add_class("btn-secondary")
        shortcut_btn.connect("clicked", self.on_create_shortcut_clicked)

        header_box.pack_start(header_text_box, True, True, 0)
        header_box.pack_end(shortcut_btn, False, False, 0)
        main_vbox.pack_start(header_box, False, False, 0)

        # 2. Live Battery Dashboard Card
        dash_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        dash_card.get_style_context().add_class("card")

        dash_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        dash_title = Gtk.Label(label="Current Battery Status", xalign=0)
        dash_title.get_style_context().add_class("card-title")
        
        self.service_badge = Gtk.Label(label="Boot Persistence: Checking...")
        self.service_badge.get_style_context().add_class("badge")
        self.service_badge.get_style_context().add_class("badge-info")
        
        dash_header.pack_start(dash_title, True, True, 0)
        dash_header.pack_end(self.service_badge, False, False, 0)
        dash_card.pack_start(dash_header, False, False, 0)

        # Status Grid
        grid = Gtk.Grid()
        grid.set_column_spacing(24)
        grid.set_row_spacing(8)

        # Charge Level
        lbl1 = Gtk.Label(label="Current Level", xalign=0)
        lbl1.get_style_context().add_class("header-subtitle")
        self.cap_val_lbl = Gtk.Label(label="-- %", xalign=0)
        self.cap_val_lbl.get_style_context().add_class("status-value")
        grid.attach(lbl1, 0, 0, 1, 1)
        grid.attach(self.cap_val_lbl, 0, 1, 1, 1)

        # Active Limit
        lbl2 = Gtk.Label(label="Active Hardware Limit", xalign=0)
        lbl2.get_style_context().add_class("header-subtitle")
        self.thresh_val_lbl = Gtk.Label(label="-- %", xalign=0)
        self.thresh_val_lbl.get_style_context().add_class("status-value")
        grid.attach(lbl2, 1, 0, 1, 1)
        grid.attach(self.thresh_val_lbl, 1, 1, 1, 1)

        # Charging State
        lbl3 = Gtk.Label(label="Power Status", xalign=0)
        lbl3.get_style_context().add_class("header-subtitle")
        self.status_val_lbl = Gtk.Label(label="Unknown", xalign=0)
        self.status_val_lbl.get_style_context().add_class("card-title")
        grid.attach(lbl3, 2, 0, 1, 1)
        grid.attach(self.status_val_lbl, 2, 1, 1, 1)

        dash_card.pack_start(grid, False, False, 0)

        # Visual Battery Level Bar
        self.level_bar = Gtk.LevelBar()
        self.level_bar.set_min_value(0.0)
        self.level_bar.set_max_value(1.0)
        self.level_bar.set_value(0.95)
        dash_card.pack_start(self.level_bar, False, False, 0)

        main_vbox.pack_start(dash_card, False, False, 0)

        # Explanatory Info Note on Battery Behavior
        note_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        note_box.get_style_context().add_class("info-note")
        self.note_lbl = Gtk.Label(
            label="💡 Tip: Run 'sudo ./limitd.sh <limit>' or 'sudo ./install.sh' in your terminal if authorization is required.",
            xalign=0
        )
        self.note_lbl.set_line_wrap(True)
        note_box.pack_start(self.note_lbl, False, False, 0)
        main_vbox.pack_start(note_box, False, False, 0)

        # 3. Decision Guidance & Presets
        decision_label = Gtk.Label(label="Choose Your Recommended Limit", xalign=0)
        decision_label.get_style_context().add_class("card-title")
        main_vbox.pack_start(decision_label, False, False, 0)

        presets = [
            (60, "🌿 Maximum Lifespan (60%)", "Best if plugged in continuously on AC power. Minimizes voltage stress."),
            (80, "⚖️ Daily Balance (80%)", "Recommended preset! Excellent mix of battery health & mobility."),
            (100, "✈️ Full Capacity (100%)", "Maximum runtime for long trips, travel, or off-grid usage.")
        ]

        presets_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        for pct, title, desc in presets:
            btn = Gtk.Button()
            btn.get_style_context().add_class("preset-card")
            
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            t_lbl = Gtk.Label(label=title, xalign=0)
            t_lbl.get_style_context().add_class("preset-title")
            d_lbl = Gtk.Label(label=desc, xalign=0)
            d_lbl.get_style_context().add_class("preset-subtitle")
            d_lbl.set_line_wrap(True)

            box.pack_start(t_lbl, False, False, 0)
            box.pack_start(d_lbl, False, False, 0)
            btn.add(box)

            btn.connect("clicked", self.on_preset_clicked, pct)
            presets_box.pack_start(btn, False, False, 0)
            self.preset_widgets[pct] = btn

        main_vbox.pack_start(presets_box, False, False, 0)

        # 4. Custom Slider Control
        custom_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        custom_box.get_style_context().add_class("card")

        slider_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        slider_title = Gtk.Label(label="Custom Threshold Adjustment", xalign=0)
        slider_title.get_style_context().add_class("card-title")
        self.slider_val_lbl = Gtk.Label(label="80%", xalign=1)
        self.slider_val_lbl.get_style_context().add_class("preset-title")
        
        slider_header.pack_start(slider_title, True, True, 0)
        slider_header.pack_end(self.slider_val_lbl, False, False, 0)
        custom_box.pack_start(slider_header, False, False, 0)

        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 50, 100, 5)
        self.scale.set_value(80)
        self.scale.set_draw_value(False)
        self.scale.connect("value-changed", self.on_scale_changed)
        custom_box.pack_start(self.scale, False, False, 0)

        main_vbox.pack_start(custom_box, False, False, 0)

        # 5. Apply Button & Notification
        self.apply_btn = Gtk.Button(label="Apply & Save Limit (Persists on Reboot)")
        self.apply_btn.get_style_context().add_class("btn-primary")
        self.apply_btn.connect("clicked", self.on_apply_clicked)
        main_vbox.pack_start(self.apply_btn, False, False, 0)

        # Notification area
        self.notification_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.notification_box.get_style_context().add_class("notification-box")
        self.notification_lbl = Gtk.Label(label="", xalign=0)
        self.notification_lbl.set_line_wrap(True)
        self.notification_box.pack_start(self.notification_lbl, True, True, 0)
        self.notification_box.set_no_show_all(True)
        self.notification_box.hide()
        main_vbox.pack_start(self.notification_box, False, False, 0)

        self.update_preset_selection(80)

    def refresh_status(self):
        info = battery_limiter_backend.get_battery_info()
        cap = info.get("capacity")
        thresh = info.get("threshold")
        stat = info.get("status", "Unknown")
        svc = info.get("service_enabled", False)

        if cap is not None:
            self.cap_val_lbl.set_text(f"{cap}%")
            self.level_bar.set_value(cap / 100.0)
        else:
            self.cap_val_lbl.set_text("N/A")

        if thresh is not None:
            self.thresh_val_lbl.set_text(f"{thresh}%")
        else:
            self.thresh_val_lbl.set_text("N/A")

        self.status_val_lbl.set_text(stat)

        if cap is not None and thresh is not None and cap >= thresh and thresh < 100:
            self.note_lbl.set_text(
                f"⚡ Hardware Limit Active ({thresh}%): Your battery level ({cap}%) is at/above the limit. "
                f"Charging is hardware-stopped! Battery will discharge or hold at {thresh}%."
            )
        elif cap is not None and thresh is not None:
            self.note_lbl.set_text(
                f"⚡ Hardware Limit Active ({thresh}%): Battery will stop charging once it reaches {thresh}%."
            )

        if svc:
            self.service_badge.set_text("✓ Boot Persistent (systemd enabled)")
            self.service_badge.get_style_context().remove_class("badge-info")
            self.service_badge.get_style_context().add_class("badge-success")
        else:
            self.service_badge.set_text("Boot Persistence: Not Enabled")
            self.service_badge.get_style_context().remove_class("badge-success")
            self.service_badge.get_style_context().add_class("badge-info")

        return True

    def on_preset_clicked(self, btn, target):
        self.scale.set_value(target)
        self.update_preset_selection(target)

    def on_scale_changed(self, scale):
        val = int(scale.get_value())
        self.selected_target = val
        self.slider_val_lbl.set_text(f"{val}%")
        self.update_preset_selection(val)

    def update_preset_selection(self, selected_val):
        for pct, btn in self.preset_widgets.items():
            ctx = btn.get_style_context()
            if pct == selected_val:
                ctx.add_class("preset-card-selected")
            else:
                ctx.remove_class("preset-card-selected")

    def show_notification(self, message, success=True):
        self.notification_lbl.set_text(message)
        ctx = self.notification_box.get_style_context()
        if success:
            ctx.remove_class("notification-error")
            ctx.add_class("notification-success")
        else:
            ctx.remove_class("notification-success")
            ctx.add_class("notification-error")
        self.notification_box.show_all()

    def on_create_shortcut_clicked(self, btn):
        ok, res = create_desktop_shortcut()
        if ok:
            self.show_notification(f"Desktop shortcut created: {res}", True)
        else:
            self.show_notification(f"Could not create desktop shortcut: {res}", False)

    def on_apply_clicked(self, btn):
        target = self.selected_target
        backend_script = os.path.abspath("battery_limiter_backend.py")

        if os.geteuid() == 0:
            success, msg = battery_limiter_backend.apply_limit(target)
        else:
            # 1. Try sudo without password first
            cmd_sudo = ["sudo", "-n", sys.executable, backend_script, "set", str(target)]
            try:
                res = subprocess.run(cmd_sudo, capture_output=True, text=True)
                if res.returncode == 0:
                    success = True
                    msg = res.stdout.strip() or f"Successfully set charge limit to {target}%!"
                else:
                    # 2. Try pkexec (Graphical Password Dialog)
                    env = os.environ.copy()
                    cmd_pkexec = ["pkexec", sys.executable, backend_script, "set", str(target)]
                    res_pk = subprocess.run(cmd_pkexec, capture_output=True, text=True, env=env)
                    if res_pk.returncode == 0:
                        success = True
                        msg = res_pk.stdout.strip() or f"Successfully set charge limit to {target}%!"
                    else:
                        # 3. Fallback: Launch terminal password prompt
                        term_cmd = [
                            "x-terminal-emulator", "-e",
                            f"bash -c 'echo Requesting root permissions to set battery limit to {target}%...; sudo {sys.executable} {backend_script} set {target}; echo Press enter to close...; read'"
                        ]
                        try:
                            subprocess.Popen(term_cmd)
                            success = True
                            msg = f"Opened terminal prompt to enter sudo password and set limit to {target}%!"
                        except Exception as te:
                            success = False
                            msg = f"Please run in terminal: sudo ./limitd.sh {target}"
            except Exception as e:
                success = False
                msg = f"Failed to execute authorization command: {e}"

        self.show_notification(msg, success=success)
        # Small delay then refresh status
        GLib.timeout_add(1000, self.refresh_status)

def main():
    app = BatteryLimiterApp()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
