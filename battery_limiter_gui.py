#!/usr/bin/env python3
"""
Battery Charge Limiter GUI for Linux (GTK 3).
A modern, beautiful, and intuitive battery threshold manager with:
- Instant UI synchronization across live battery status, target profiles, and percentages
- Dark and Light theme support with instant toggle & persistence
- Universal support for Lenovo, ASUS, Dell, LG Gram, Samsung, Huawei, Framework, System76, Sony, MSI, Apple Silicon
"""

import sys
import os
import json
import subprocess

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

import battery_limiter_backend

HELPER_PATH = "/usr/local/bin/battery-limiter-helper"
CONFIG_DIR = os.path.expanduser("~/.config/battery-limiter")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


def load_config():
    """Loads user configuration (such as theme preference)."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"theme": "dark"}


def save_config(cfg):
    """Saves user configuration."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"Notice: Could not save config: {e}", file=sys.stderr)


CSS_DARK = b"""
* {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Ubuntu, "Helvetica Neue", sans-serif;
    color: #f1f5f9;
}
window, window.background {
    background-color: #0d121d;
    color: #f1f5f9;
}
scrolledwindow, viewport {
    background-color: #0d121d;
    border: none;
}
box, grid {
    background-color: transparent;
}
label {
    color: #f1f5f9;
    text-shadow: none;
}

/* Card surfaces */
.card {
    background-color: #141b29;
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid #232e42;
}
.hardware-card {
    background-color: #101622;
    border-radius: 12px;
    padding: 12px 14px;
    border: 1px solid #1e2838;
}
.hw-label {
    font-size: 11px;
    font-weight: 700;
    color: #38bdf8;
}
.hw-value {
    font-size: 13px;
    font-weight: 700;
    color: #ffffff;
}
.hw-sub {
    font-size: 11px;
    color: #94a3b8;
}
.header-title {
    font-size: 20px;
    font-weight: 800;
    color: #ffffff;
}
.header-subtitle {
    font-size: 11px;
    color: #94a3b8;
}
.section-heading {
    font-size: 12px;
    font-weight: 700;
    color: #e2e8f0;
}
.status-val-big {
    font-size: 34px;
    font-weight: 800;
    color: #38bdf8;
}
.status-meta-title {
    font-size: 10px;
    font-weight: 700;
    color: #64748b;
}
.status-meta-val {
    font-size: 13px;
    font-weight: 700;
    color: #ffffff;
}

/* All Buttons Uniform Dark Reset */
button {
    background-color: #141b29;
    background-image: none;
    box-shadow: none;
    text-shadow: none;
    border: 1px solid #232e42;
    border-radius: 8px;
    color: #f1f5f9;
}
button label {
    color: #f1f5f9;
    text-shadow: none;
}
button:hover {
    background-color: #1d273b;
    border-color: #38bdf8;
}

/* Preset Cards */
button.preset-card {
    background-color: #101622;
    border: 2px solid #1e2838;
    border-radius: 12px;
    padding: 12px 14px;
    color: #f1f5f9;
}
button.preset-card:hover {
    background-color: #192336;
    border-color: #38bdf8;
}
button.preset-card.preset-card-selected {
    background-color: #0b2545;
    border: 2px solid #38bdf8;
}
button.preset-card label.preset-title {
    font-size: 13px;
    font-weight: 700;
    color: #38bdf8;
}
button.preset-card.preset-card-selected label.preset-title {
    color: #38bdf8;
}
button.preset-card label.preset-desc {
    font-size: 11px;
    color: #94a3b8;
}
button.preset-card label.preset-badge-lbl {
    font-size: 10px;
    font-weight: 700;
    color: #38bdf8;
}

/* Slider & Pills */
.slider-val-label {
    font-size: 20px;
    font-weight: 800;
    color: #38bdf8;
}
button.btn-pill {
    background-color: #101622;
    border: 1px solid #232e42;
    border-radius: 6px;
    padding: 6px 10px;
}
button.btn-pill label {
    color: #cbd5e1;
    font-size: 11px;
    font-weight: 600;
}
button.btn-pill:hover {
    background-color: #1d273b;
    border-color: #38bdf8;
}
button.btn-pill.btn-pill-active {
    background-color: #0284c7;
    border: 1px solid #38bdf8;
}
button.btn-pill.btn-pill-active label {
    color: #ffffff;
    font-weight: 800;
}

/* Primary Apply Button */
button.btn-primary {
    background-color: #0284c7;
    border: 1px solid #38bdf8;
    border-radius: 10px;
    padding: 12px 20px;
}
button.btn-primary label {
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
}
button.btn-primary:hover {
    background-color: #0369a1;
}

/* Secondary Button */
button.btn-secondary {
    background-color: #141b29;
    border: 1px solid #232e42;
    border-radius: 8px;
    padding: 6px 12px;
}
button.btn-secondary label {
    color: #cbd5e1;
    font-size: 11px;
    font-weight: 600;
}
button.btn-secondary:hover {
    background-color: #1d273b;
    border-color: #38bdf8;
}

/* Badges */
.badge {
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 10px;
    font-weight: 700;
}
.badge-success { background-color: #064e3b; color: #6ee7b7; border: 1px solid #047857; }
.badge-warning { background-color: #78350f; color: #fde68a; border: 1px solid #b45309; }
.badge-info    { background-color: #0c4a6e; color: #7dd3fc; border: 1px solid #0369a1; }
.badge-error   { background-color: #45131e; color: #fca5a5; border: 1px solid #991b1b; }

/* Notice Box */
.notice-box {
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 12px;
}
.notice-info    { background-color: #082f49; border: 1px solid #0369a1; color: #7dd3fc; }
.notice-success { background-color: #064e3b; border: 1px solid #047857; color: #86efac; }
.notice-warning { background-color: #451a03; border: 1px solid #78350f; color: #fde047; }
.notice-error   { background-color: #45131e; border: 1px solid #991b1b; color: #fca5a5; }

.info-tip {
    font-size: 11px;
    color: #94a3b8;
}

/* Scale styling */
scale trough {
    background-color: #1e2838;
    border-radius: 6px;
    min-height: 8px;
    border: none;
}
scale highlight {
    background-color: #0284c7;
    border-radius: 6px;
}
scale slider {
    background-color: #38bdf8;
    border: 2px solid #ffffff;
    border-radius: 50%;
    min-width: 18px;
    min-height: 18px;
}

/* LevelBar styling */
levelbar trough {
    background-color: #1e2838;
    border-radius: 6px;
    padding: 2px;
    min-height: 10px;
}
levelbar block {
    background-color: #0284c7;
    border-radius: 4px;
}
levelbar block.filled {
    background-color: #38bdf8;
}
levelbar block.empty {
    background-color: #1e2838;
}
levelbar block.full {
    background-color: #10b981;
}
levelbar block.high {
    background-color: #38bdf8;
}
levelbar block.low {
    background-color: #f59e0b;
}
"""

CSS_LIGHT = b"""
* {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Ubuntu, "Helvetica Neue", sans-serif;
    color: #0f172a;
}
window, window.background {
    background-color: #f1f5f9;
    color: #0f172a;
}
scrolledwindow, viewport {
    background-color: #f1f5f9;
    border: none;
}
box, grid {
    background-color: transparent;
}
label {
    color: #0f172a;
    text-shadow: none;
}

/* Card surfaces */
.card {
    background-color: #ffffff;
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid #cbd5e1;
}
.hardware-card {
    background-color: #f8fafc;
    border-radius: 12px;
    padding: 12px 14px;
    border: 1px solid #cbd5e1;
}
.hw-label {
    font-size: 11px;
    font-weight: 700;
    color: #0284c7;
}
.hw-value {
    font-size: 13px;
    font-weight: 700;
    color: #0f172a;
}
.hw-sub {
    font-size: 11px;
    color: #475569;
}
.header-title {
    font-size: 20px;
    font-weight: 800;
    color: #0f172a;
}
.header-subtitle {
    font-size: 11px;
    color: #475569;
}
.section-heading {
    font-size: 12px;
    font-weight: 700;
    color: #334155;
}
.status-val-big {
    font-size: 34px;
    font-weight: 800;
    color: #0284c7;
}
.status-meta-title {
    font-size: 10px;
    font-weight: 700;
    color: #64748b;
}
.status-meta-val {
    font-size: 13px;
    font-weight: 700;
    color: #0f172a;
}

/* Buttons in Light Theme */
button {
    background-color: #ffffff;
    background-image: none;
    box-shadow: none;
    text-shadow: none;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    color: #0f172a;
}
button label {
    color: #0f172a;
    text-shadow: none;
}
button:hover {
    background-color: #f1f5f9;
    border-color: #0284c7;
}

/* Preset Cards */
button.preset-card {
    background-color: #ffffff;
    border: 2px solid #e2e8f0;
    border-radius: 12px;
    padding: 12px 14px;
    color: #0f172a;
}
button.preset-card:hover {
    background-color: #f8fafc;
    border-color: #0284c7;
}
button.preset-card.preset-card-selected {
    background-color: #e0f2fe;
    border: 2px solid #0284c7;
}
button.preset-card label.preset-title {
    font-size: 13px;
    font-weight: 700;
    color: #0284c7;
}
button.preset-card.preset-card-selected label.preset-title {
    color: #0284c7;
}
button.preset-card label.preset-desc {
    font-size: 11px;
    color: #475569;
}
button.preset-card label.preset-badge-lbl {
    font-size: 10px;
    font-weight: 700;
    color: #0284c7;
}

/* Slider & Pills */
.slider-val-label {
    font-size: 20px;
    font-weight: 800;
    color: #0284c7;
}
button.btn-pill {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 10px;
}
button.btn-pill label {
    color: #334155;
    font-size: 11px;
    font-weight: 600;
}
button.btn-pill:hover {
    background-color: #f1f5f9;
    border-color: #0284c7;
}
button.btn-pill.btn-pill-active {
    background-color: #0284c7;
    border: 1px solid #0369a1;
}
button.btn-pill.btn-pill-active label {
    color: #ffffff;
    font-weight: 800;
}

/* Primary Apply Button */
button.btn-primary {
    background-color: #0284c7;
    border: 1px solid #0369a1;
    border-radius: 10px;
    padding: 12px 20px;
}
button.btn-primary label {
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
}
button.btn-primary:hover {
    background-color: #0369a1;
}

/* Secondary Button */
button.btn-secondary {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 6px 12px;
}
button.btn-secondary label {
    color: #334155;
    font-size: 11px;
    font-weight: 600;
}
button.btn-secondary:hover {
    background-color: #f1f5f9;
    border-color: #0284c7;
}

/* Badges */
.badge {
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 10px;
    font-weight: 700;
}
.badge-success { background-color: #dcfce7; color: #15803d; border: 1px solid #86efac; }
.badge-warning { background-color: #fef3c7; color: #b45309; border: 1px solid #fde68a; }
.badge-info    { background-color: #e0f2fe; color: #0369a1; border: 1px solid #7dd3fc; }
.badge-error   { background-color: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }

/* Notice Box */
.notice-box {
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 12px;
}
.notice-info    { background-color: #e0f2fe; border: 1px solid #7dd3fc; color: #0369a1; }
.notice-success { background-color: #dcfce7; border: 1px solid #86efac; color: #15803d; }
.notice-warning { background-color: #fef3c7; border: 1px solid #fde68a; color: #b45309; }
.notice-error   { background-color: #fee2e2; border: 1px solid #fca5a5; color: #b91c1c; }

.info-tip {
    font-size: 11px;
    color: #475569;
}

/* Scale styling */
scale trough {
    background-color: #cbd5e1;
    border-radius: 6px;
    min-height: 8px;
    border: none;
}
scale highlight {
    background-color: #0284c7;
    border-radius: 6px;
}
scale slider {
    background-color: #0284c7;
    border: 2px solid #ffffff;
    border-radius: 50%;
    min-width: 18px;
    min-height: 18px;
}

/* LevelBar styling */
levelbar trough {
    background-color: #e2e8f0;
    border-radius: 6px;
    padding: 2px;
    min-height: 10px;
}
levelbar block {
    background-color: #0284c7;
    border-radius: 4px;
}
levelbar block.filled {
    background-color: #0284c7;
}
levelbar block.empty {
    background-color: #e2e8f0;
}
levelbar block.full {
    background-color: #10b981;
}
levelbar block.high {
    background-color: #0284c7;
}
levelbar block.low {
    background-color: #f59e0b;
}
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
        "Keywords=battery;charge;limit;threshold;lenovo;asus;dell;laptop;health;\n"
    )
    if os.path.isdir(desktop_dir):
        target = os.path.join(desktop_dir, "battery-limiter.desktop")
        try:
            with open(target, "w", encoding="utf-8") as f:
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
        self.set_default_size(560, 840)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.get_style_context().add_class("main-window")

        # Load persisted configuration (theme preference)
        self.config = load_config()
        self.current_theme = self.config.get("theme", "dark")
        self.css_provider = Gtk.CssProvider()
        self._updating_scale = False

        self._apply_theme(self.current_theme)

        self.info = battery_limiter_backend.get_battery_info()
        self.selected_target = self.info.get("threshold") or 60
        self.preset_widgets = {}
        self.preset_badge_labels = {}
        self.pill_buttons = {}

        self.build_ui()
        self.refresh_status()
        GLib.timeout_add_seconds(3, self.refresh_status)

    def _apply_theme(self, theme_name):
        """Applies dark or light theme CSS and updates GTK window settings."""
        self.current_theme = theme_name
        settings = Gtk.Settings.get_default()
        if settings:
            settings.set_property("gtk-application-prefer-dark-theme", (theme_name == "dark"))

        css_data = CSS_DARK if theme_name == "dark" else CSS_LIGHT
        try:
            self.css_provider.load_from_data(css_data)
            screen = Gdk.Screen.get_default()
            if screen:
                Gtk.StyleContext.add_provider_for_screen(
                    screen, self.css_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
        except Exception as e:
            print(f"Notice: CSS styling note: {e}", file=sys.stderr)

        if hasattr(self, "theme_btn"):
            if theme_name == "dark":
                self.theme_btn.set_label("☀️ Light Mode")
                self.theme_btn.set_tooltip_text("Switch to Light Theme")
            else:
                self.theme_btn.set_label("🌙 Dark Mode")
                self.theme_btn.set_tooltip_text("Switch to Dark Theme")

        if hasattr(self, "selected_target"):
            self._update_selection(self.selected_target)

    def toggle_theme(self):
        """Toggles between dark and light themes and persists preference."""
        new_theme = "light" if self.current_theme == "dark" else "dark"
        self._apply_theme(new_theme)
        self.config["theme"] = new_theme
        save_config(self.config)

    def build_ui(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.add(scroll)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.set_margin_top(16)
        root.set_margin_bottom(16)
        root.set_margin_left(20)
        root.set_margin_right(20)
        scroll.add(root)

        # ── 1. Header ────────────────────────────────────────────────────────
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hdr_txt = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        ttl = Gtk.Label(label="⚡ Battery Charge Limiter", xalign=0)
        ttl.get_style_context().add_class("header-title")
        sub = Gtk.Label(
            label="Extend battery lifespan with smart charge threshold management",
            xalign=0, wrap=True
        )
        sub.get_style_context().add_class("header-subtitle")
        hdr_txt.pack_start(ttl, False, False, 0)
        hdr_txt.pack_start(sub, False, False, 0)

        hdr_btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # Theme Switcher button
        theme_label = "☀️ Light Mode" if self.current_theme == "dark" else "🌙 Dark Mode"
        self.theme_btn = Gtk.Button(label=theme_label)
        self.theme_btn.get_style_context().add_class("btn-secondary")
        self.theme_btn.set_tooltip_text("Toggle Dark / Light Theme")
        self.theme_btn.connect("clicked", lambda _: self.toggle_theme())

        # Refresh button
        refresh_btn = Gtk.Button(label="🔄")
        refresh_btn.get_style_context().add_class("btn-secondary")
        refresh_btn.set_tooltip_text("Refresh battery status")
        refresh_btn.connect("clicked", lambda _: self.refresh_status())

        # Shortcut button
        shortcut_btn = Gtk.Button(label="📌 Desktop")
        shortcut_btn.get_style_context().add_class("btn-secondary")
        shortcut_btn.set_tooltip_text("Create a Desktop shortcut")
        shortcut_btn.connect("clicked", lambda _: self._do_desktop_shortcut())

        hdr_btns.pack_start(self.theme_btn, False, False, 0)
        hdr_btns.pack_start(refresh_btn, False, False, 0)
        hdr_btns.pack_start(shortcut_btn, False, False, 0)

        hdr.pack_start(hdr_txt, True, True, 0)
        hdr.pack_end(hdr_btns, False, False, 0)
        root.pack_start(hdr, False, False, 0)

        # ── 2. Detected Hardware Card ────────────────────────────────────────
        hw_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        hw_card.get_style_context().add_class("hardware-card")

        hw_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.laptop_lbl = Gtk.Label(label="", xalign=0)
        self.laptop_lbl.get_style_context().add_class("hw-value")
        self.driver_badge = Gtk.Label(label="")
        self.driver_badge.get_style_context().add_class("badge")
        self.driver_badge.get_style_context().add_class("badge-info")
        hw_top.pack_start(self.laptop_lbl, True, True, 0)
        hw_top.pack_end(self.driver_badge, False, False, 0)
        hw_card.pack_start(hw_top, False, False, 0)

        self.bat_sub_lbl = Gtk.Label(label="", xalign=0)
        self.bat_sub_lbl.get_style_context().add_class("hw-sub")
        hw_card.pack_start(self.bat_sub_lbl, False, False, 0)

        root.pack_start(hw_card, False, False, 0)

        # ── 3. Live Battery & Profile Status Card ────────────────────────────
        status_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        status_card.get_style_context().add_class("card")

        status_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        sec_title = Gtk.Label(label="Live Battery & Active Profile", xalign=0)
        sec_title.get_style_context().add_class("section-heading")
        self.service_badge = Gtk.Label(label="")
        self.service_badge.get_style_context().add_class("badge")
        status_hdr.pack_start(sec_title, True, True, 0)
        status_hdr.pack_end(self.service_badge, False, False, 0)
        status_card.pack_start(status_hdr, False, False, 0)

        # Grid stats
        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(6)
        grid.set_column_homogeneous(True)

        def stat_col(title, row=0, col=0):
            lbl = Gtk.Label(label=title, xalign=0)
            lbl.get_style_context().add_class("status-meta-title")
            val = Gtk.Label(label="--", xalign=0)
            val.get_style_context().add_class("status-meta-val")
            grid.attach(lbl, col, row, 1, 1)
            grid.attach(val, col, row + 1, 1, 1)
            return val

        # Big live percentage display
        self.cap_val_lbl = Gtk.Label(label="--%", xalign=0)
        self.cap_val_lbl.get_style_context().add_class("status-val-big")

        cap_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        cap_title = Gtk.Label(label="CURRENT BATTERY", xalign=0)
        cap_title.get_style_context().add_class("status-meta-title")
        cap_box.pack_start(cap_title, False, False, 0)
        cap_box.pack_start(self.cap_val_lbl, False, False, 0)
        grid.attach(cap_box, 0, 0, 1, 2)

        self.thresh_lbl = stat_col("ACTIVE LIMIT", row=0, col=1)
        self.status_lbl = stat_col("POWER STATE", row=0, col=2)

        # Selected Target Profile live readout
        self.target_profile_lbl = stat_col("TARGET SELECTION", row=2, col=1)
        self.health_mode_lbl = stat_col("CONSERVATION STATE", row=2, col=2)

        status_card.pack_start(grid, False, False, 0)

        self.level_bar = Gtk.LevelBar()
        self.level_bar.set_min_value(0.0)
        self.level_bar.set_max_value(1.0)
        self.level_bar.set_value(0.0)
        status_card.pack_start(self.level_bar, False, False, 0)

        root.pack_start(status_card, False, False, 0)

        # ── 4. Target Threshold Presets ──────────────────────────────────────
        choose_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        choose_lbl = Gtk.Label(label="Choose Your Battery Profile", xalign=0)
        choose_lbl.get_style_context().add_class("section-heading")
        self.target_badge = Gtk.Label(label=f"🎯 Target: {self.selected_target}%", xalign=1)
        self.target_badge.get_style_context().add_class("badge")
        self.target_badge.get_style_context().add_class("badge-info")

        choose_hdr.pack_start(choose_lbl, True, True, 0)
        choose_hdr.pack_end(self.target_badge, False, False, 0)
        root.pack_start(choose_hdr, False, False, 0)

        presets = [
            (60, "🌿 Maximum Lifespan (60%)",
             "Recommended for continuous AC power / desk work. Minimizes battery voltage stress & heat build-up."),
            (80, "⚖️ Daily Balance (80%)",
             "Recommended for daily mixed use. Balances chemical longevity with sufficient mobile battery run-time."),
            (100, "✈️ Full Capacity (100%)",
             "For travel, flights, or long off-grid work. Charges battery to full 100% capacity."),
        ]

        self.presets_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for val, title, desc in presets:
            btn = Gtk.Button()
            btn.get_style_context().add_class("preset-card")
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)

            top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            t = Gtk.Label(label=title, xalign=0)
            t.get_style_context().add_class("preset-title")
            badge_lbl = Gtk.Label(label="", xalign=1)
            badge_lbl.get_style_context().add_class("preset-badge-lbl")
            top_row.pack_start(t, True, True, 0)
            top_row.pack_end(badge_lbl, False, False, 0)

            d = Gtk.Label(label=desc, xalign=0)
            d.get_style_context().add_class("preset-desc")
            d.set_line_wrap(True)

            inner.pack_start(top_row, False, False, 0)
            inner.pack_start(d, False, False, 0)
            btn.add(inner)
            btn.connect("clicked", self._on_preset_click, val)
            self.presets_box.pack_start(btn, False, False, 0)
            self.preset_widgets[val] = btn
            self.preset_badge_labels[val] = badge_lbl

        root.pack_start(self.presets_box, False, False, 0)

        # ── 5. Fine Slider & Quick Select Pills ──────────────────────────────
        slider_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        slider_card.get_style_context().add_class("card")

        slider_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        slider_title = Gtk.Label(label="Precision Target Slider", xalign=0)
        slider_title.get_style_context().add_class("section-heading")
        self.slider_lbl = Gtk.Label(label=f"{self.selected_target}%", xalign=1)
        self.slider_lbl.get_style_context().add_class("slider-val-label")
        slider_hdr.pack_start(slider_title, True, True, 0)
        slider_hdr.pack_end(self.slider_lbl, False, False, 0)
        slider_card.pack_start(slider_hdr, False, False, 0)

        # Quick select pill buttons
        pills_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        pills_box.set_homogeneous(True)
        for pval in [50, 60, 70, 80, 90, 100]:
            pbtn = Gtk.Button(label=f"{pval}%")
            pbtn.get_style_context().add_class("btn-pill")
            pbtn.connect("clicked", self._on_pill_click, pval)
            pills_box.pack_start(pbtn, True, True, 0)
            self.pill_buttons[pval] = pbtn
        slider_card.pack_start(pills_box, False, False, 0)

        # Continuous scale
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 50, 100, 5)
        self.scale.set_value(self.selected_target)
        self.scale.set_draw_value(False)
        self.scale.connect("value-changed", self._on_scale_change)
        slider_card.pack_start(self.scale, False, False, 0)

        # Hardware explanatory tip
        self.hw_tip_lbl = Gtk.Label(label="", xalign=0)
        self.hw_tip_lbl.get_style_context().add_class("info-tip")
        self.hw_tip_lbl.set_line_wrap(True)
        slider_card.pack_start(self.hw_tip_lbl, False, False, 0)

        root.pack_start(slider_card, False, False, 0)

        # ── 6. Apply Button ──────────────────────────────────────────────────
        self.apply_btn = Gtk.Button(label=f"⚡ Apply {self.selected_target}% Limit & Save (Persists on Reboot)")
        self.apply_btn.get_style_context().add_class("btn-primary")
        self.apply_btn.connect("clicked", self._on_apply)
        root.pack_start(self.apply_btn, False, False, 0)

        # ── 7. Result Feedback Notice ────────────────────────────────────────
        self.result_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.result_box.get_style_context().add_class("notice-box")
        self.result_lbl = Gtk.Label(label="", xalign=0)
        self.result_lbl.set_line_wrap(True)
        self.result_box.pack_start(self.result_lbl, False, False, 0)
        self.result_box.set_no_show_all(True)
        self.result_box.hide()
        root.pack_start(self.result_box, False, False, 0)

        # ── 8. Auth notice (bottom) ──────────────────────────────────────────
        self.auth_notice = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.auth_notice.get_style_context().add_class("notice-box")
        self.auth_lbl = Gtk.Label(label="", xalign=0)
        self.auth_lbl.set_line_wrap(True)
        self.auth_notice.pack_start(self.auth_lbl, False, False, 0)
        root.pack_start(self.auth_notice, False, False, 0)

        self._update_selection(self.selected_target)

    # ── Status Refresh ────────────────────────────────────────────────────────

    def refresh_status(self):
        info = battery_limiter_backend.get_battery_info()
        self.info = info

        laptop = info.get("laptop", {})
        interface = info.get("interface", {})
        cap = info.get("capacity")
        thresh_display = info.get("threshold_display", "N/A")
        is_conservation_active = info.get("is_conservation_active", False)
        stat = info.get("status", "Unknown")
        svc = info.get("service_enabled", False)
        manufacturer = info.get("manufacturer", "")
        model = info.get("model", "")
        bat_path = info.get("bat_path", "")
        bat_name = os.path.basename(bat_path) if bat_path else "BAT"
        cycles = info.get("cycle_count")
        can_write = info.get("can_write_direct", False)
        helper_ok = info.get("helper_installed", False)
        is_root = info.get("is_root", False)
        ac_online = info.get("ac_online")

        # Hardware display
        disp_name = laptop.get("display_name", "Linux Laptop")
        driver_type = interface.get("type", "")
        if driver_type == "conservation_mode":
            driver_short = "Lenovo Conservation Mode (ideapad_laptop)"
        elif driver_type == "percentage":
            driver_short = "Standard sysfs (charge_control_end_threshold)"
        elif driver_type == "lg_care":
            driver_short = "LG Battery Care (lg_laptop)"
        elif driver_type == "samsung_extender":
            driver_short = "Samsung Extender"
        else:
            driver_short = interface.get("driver_name", "Hardware ACPI")

        self.laptop_lbl.set_text(f"💻 {disp_name}")
        self.driver_badge.set_text(driver_short)

        # Battery Subtitle
        sub_text = f"🔋 {manufacturer} {model} ({bat_name})"
        if cycles:
            sub_text += f"   •   🔄 Cycle Count: {cycles}"
        if ac_online is True:
            sub_text += "   •   🔌 AC Charger Connected"
        elif ac_online is False:
            sub_text += "   •   🔋 On Battery Power"
        self.bat_sub_lbl.set_text(sub_text)

        # Stats
        self.cap_val_lbl.set_text(f"{cap}%" if cap is not None else "--%")
        self.thresh_lbl.set_text(thresh_display)
        self.status_lbl.set_text(stat)
        if cap is not None:
            self.level_bar.set_value(cap / 100.0)

        # Conservation state readout
        if driver_type == "conservation_mode":
            if is_conservation_active:
                self.health_mode_lbl.set_text("Active (55-60% Cap)")
            else:
                self.health_mode_lbl.set_text("Disabled (100% Full)")
        elif driver_type == "percentage":
            self.health_mode_lbl.set_text(f"{thresh_display} Threshold")
        else:
            self.health_mode_lbl.set_text(thresh_display)

        # Persistence badge
        ctx = self.service_badge.get_style_context()
        for cls in ["badge-success", "badge-info", "badge-warning"]:
            ctx.remove_class(cls)
        if svc:
            self.service_badge.set_text("✓ Persists on Boot & Sleep")
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
                "✅ Direct Access: Settings will apply immediately without prompt."
            )
        elif helper_ok:
            ctx2.add_class("notice-info")
            self.auth_lbl.set_text(
                "🔑 System Helper Active: A password prompt will appear when applying new limits."
            )
        else:
            ctx2.add_class("notice-warning")
            self.auth_lbl.set_text(
                "⚠️ First-time setup: Run 'sudo ./install.sh' in terminal to enable passwordless control."
            )

        # Update target profile label & hardware tip
        self._update_hardware_tip(self.selected_target)

        return True

    # ── Selection & Event Handlers ────────────────────────────────────────────

    def _on_preset_click(self, _btn, val):
        self._updating_scale = True
        self.scale.set_value(val)
        self._updating_scale = False
        self._update_selection(val)

    def _on_pill_click(self, _btn, val):
        self._updating_scale = True
        self.scale.set_value(val)
        self._updating_scale = False
        self._update_selection(val)

    def _on_scale_change(self, scale):
        if self._updating_scale:
            return
        val = int(scale.get_value())
        self._update_selection(val)

    def _update_selection(self, val):
        self.selected_target = val
        self.slider_lbl.set_text(f"{val}%")

        # Update target badge in header
        if hasattr(self, "target_badge"):
            self.target_badge.set_text(f"🎯 Target: {val}%")

        # Update target profile live label in stats grid
        if hasattr(self, "target_profile_lbl"):
            if val <= 60:
                self.target_profile_lbl.set_text(f"🌿 Lifespan ({val}%)")
            elif val <= 85:
                self.target_profile_lbl.set_text(f"⚖️ Daily ({val}%)")
            else:
                self.target_profile_lbl.set_text(f"✈️ Full ({val}%)")

        # Update Apply button label
        if hasattr(self, "apply_btn"):
            self.apply_btn.set_label(f"⚡ Apply {val}% Limit & Save (Persists on Reboot)")

        # Highlight preset card
        closest_preset = None
        min_diff = 999
        for pval in self.preset_widgets.keys():
            diff = abs(pval - val)
            if diff < min_diff:
                min_diff = diff
                closest_preset = pval

        for pval, btn in self.preset_widgets.items():
            ctx = btn.get_style_context()
            badge_lbl = self.preset_badge_labels.get(pval)
            if pval == val or (min_diff <= 10 and pval == closest_preset):
                ctx.add_class("preset-card-selected")
                if badge_lbl:
                    badge_lbl.set_text("✓ SELECTED")
            else:
                ctx.remove_class("preset-card-selected")
                if badge_lbl:
                    badge_lbl.set_text("")

        # Highlight pill buttons
        for pval, pbtn in self.pill_buttons.items():
            ctx = pbtn.get_style_context()
            if pval == val:
                ctx.add_class("btn-pill-active")
            else:
                ctx.remove_class("btn-pill-active")

        self._update_hardware_tip(val)

    def _update_hardware_tip(self, val):
        interface = self.info.get("interface", {})
        itype = interface.get("type", "")

        if itype == "conservation_mode":
            if val <= 80:
                self.hw_tip_lbl.set_text(
                    f"💡 Target: {val}%. Lenovo Conservation Mode will be ACTIVATED. "
                    "Your laptop embedded controller (EC) will regulate charge to stay at ~55-60%."
                )
            else:
                self.hw_tip_lbl.set_text(
                    f"💡 Target: {val}%. Lenovo Conservation Mode will be DISABLED. "
                    "Battery will charge to full 100% capacity."
                )
        elif itype == "percentage":
            self.hw_tip_lbl.set_text(
                f"💡 Target: {val}%. Hardware charge threshold will stop AC charging exactly at {val}%."
            )
        elif itype == "lg_care" or itype == "samsung_extender":
            if val <= 80:
                self.hw_tip_lbl.set_text(f"💡 Target: {val}%. Hardware battery protection enabled (80% max).")
            else:
                self.hw_tip_lbl.set_text(f"💡 Target: {val}%. Full 100% charging enabled.")
        else:
            self.hw_tip_lbl.set_text(f"💡 Target limit: {val}%.")

    def _do_desktop_shortcut(self):
        ok, path = create_desktop_shortcut()
        if ok:
            self._show_result(f"Desktop shortcut created: {path}", True)
        else:
            self._show_result(f"Could not create shortcut: {path}", False)

    def _on_apply(self, _btn):
        target = self.selected_target
        self.apply_btn.set_sensitive(False)
        self.apply_btn.set_label(f"⚡ Applying {target}% Limit…")

        # Process GTK events so UI updates button state immediately
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)

        success, msg = self._apply_limit(target)
        self._show_result(msg, success)

        # Refresh status immediately to show updated hardware mode
        self.refresh_status()

        self.apply_btn.set_sensitive(True)
        self.apply_btn.set_label(f"⚡ Apply {target}% Limit & Save (Persists on Reboot)")
        GLib.timeout_add(500, self.refresh_status)

    def _apply_limit(self, target):
        """Attempts application via root helper (pkexec) -> direct write -> pkexec python -> terminal sudo."""
        info = battery_limiter_backend.get_battery_info()

        # 1. Root helper via pkexec
        if info.get("helper_installed"):
            result = self._try_pkexec_helper(target)
            if result[0]:
                return result
            if result[1] == "Authentication cancelled.":
                return False, "Authentication cancelled by user."

        # 2. Direct write if running as root
        if info.get("is_root"):
            return battery_limiter_backend.apply_limit(target)

        # 3. Direct write if udev plugdev rule is active
        if info.get("can_write_direct"):
            ok, msg = battery_limiter_backend.apply_limit(target)
            if ok:
                msg += "\n💡 Direct write successful! (Run 'sudo ./install.sh' once to enable systemd reboot persistence)."
            return ok, msg

        # 4. Fallback pkexec python backend
        result = self._try_pkexec_python(target)
        if result[0]:
            return result

        # 5. Terminal sudo fallback
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
