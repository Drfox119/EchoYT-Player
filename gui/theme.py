"""Colorful, glassy theme with user-selectable accent colors.

The stylesheet is generated from a small palette so the accent colour (and the
optional translucent "glass" look) can be swapped at runtime without a restart.
"""

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

import settings

FONT_STACK = '"Inter", "Segoe UI", "Ubuntu", "Noto Sans", "Cantarell", sans-serif'

# Friendly name -> accent hex. Shown as swatches in Settings.
ACCENTS = {
    "Blue": "#89b4fa",
    "Sapphire": "#74c7ec",
    "Sky": "#89dceb",
    "Teal": "#94e2d5",
    "Green": "#a6e3a1",
    "Yellow": "#f9e2af",
    "Peach": "#fab387",
    "Red": "#f38ba8",
    "Pink": "#f5c2e7",
    "Mauve": "#cba6f7",
    "Lavender": "#b4befe",
    "Flamingo": "#f2cdcd",
}

DEFAULT_ACCENT = settings.DEFAULT_ACCENT
DEFAULT_GLASS = settings.DEFAULT_GLASS

# Catppuccin Mocha base palette.
BASE = "#1e1e2e"
MANTLE = "#181825"
CRUST = "#11111b"
SURFACE0 = "#313244"
SURFACE1 = "#45475a"
SURFACE2 = "#585b70"
TEXT = "#cdd6f4"
SUBTEXT = "#a6adc8"
OVERLAY = "#6c7086"
GREEN = "#a6e3a1"
RED = "#f38ba8"
YELLOW = "#f9e2af"


# ----------------------------------------------------------------------
# Small colour helpers
# ----------------------------------------------------------------------

def _clamp(value):
    return max(0, min(255, int(round(value))))


def _rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(_clamp(c) for c in rgb)


def _rgba(hex_color, alpha):
    r, g, b = _rgb(hex_color)
    return f"rgba({r}, {g}, {b}, {alpha})"


def _shade(hex_color, factor):
    """``factor`` < 1 darkens toward black, > 1 lightens toward white."""

    r, g, b = _rgb(hex_color)

    if factor <= 1:
        return _hex((r * factor, g * factor, b * factor))

    t = factor - 1
    return _hex((r + (255 - r) * t, g + (255 - g) * t, b + (255 - b) * t))


def _mix(base, other, t):
    """Blend ``base`` toward ``other`` by fraction ``t``."""

    br, bg, bb = _rgb(base)
    orr, og, ob = _rgb(other)

    return _hex(
        (
            br + (orr - br) * t,
            bg + (og - bg) * t,
            bb + (ob - bb) * t,
        )
    )


# ----------------------------------------------------------------------
# Stylesheet
# ----------------------------------------------------------------------

def build_stylesheet(accent=DEFAULT_ACCENT, glass=DEFAULT_GLASS):
    """Return the full QSS for the given accent colour and glass setting."""

    accent = accent or DEFAULT_ACCENT
    accent_hover = _shade(accent, 0.88)
    accent_press = _shade(accent, 0.76)
    accent_soft = _rgba(accent, 0.22)
    accent_faint = _rgba(accent, 0.12)

    if glass:
        window_bg = (
            "qlineargradient(x1:0, y1:0, x2:1, y2:1, "
            f"stop:0 {_mix(BASE, accent, 0.14)}, "
            f"stop:0.55 {MANTLE}, stop:1 {CRUST})"
        )
        widget_bg = "transparent"
        sidebar_bg = _rgba(_mix(CRUST, accent, 0.10), 0.92)
        panel_bg = _rgba(_mix(BASE, accent, 0.04), 0.58)
        list_bg = _rgba(BASE, 0.55)
        input_bg = _rgba(_mix(SURFACE0, accent, 0.05), 0.55)
        button_bg = _rgba(SURFACE0, 0.55)
        button_hover = _rgba(_mix(SURFACE1, accent, 0.10), 0.75)
        button_press = _rgba(SURFACE2, 0.85)
        item_hover = _rgba(_mix(SURFACE1, accent, 0.08), 0.45)
        combo_view = _rgba(_mix(BASE, accent, 0.05), 0.96)
        border = _rgba(_shade(SURFACE1, 1.15), 0.55)

    else:
        window_bg = MANTLE
        widget_bg = BASE
        sidebar_bg = CRUST
        panel_bg = MANTLE
        list_bg = MANTLE
        input_bg = SURFACE0
        button_bg = SURFACE0
        button_hover = SURFACE1
        button_press = SURFACE2
        item_hover = SURFACE0
        combo_view = BASE
        border = SURFACE1

    return f"""
* {{
    font-family: {FONT_STACK};
}}

QWidget {{
    background-color: {widget_bg};
    color: {TEXT};
    font-size: 14px;
}}

QMainWindow, QDialog {{
    background: {window_bg};
}}

/* ---------------- Sidebar ---------------- */

#Sidebar {{
    background-color: {sidebar_bg};
    border-right: 1px solid {border};
}}

#AppTitle {{
    font-size: 22px;
    font-weight: 800;
    color: {TEXT};
    padding: 24px 22px 2px 22px;
}}

#AppSubtitle {{
    color: {OVERLAY};
    font-size: 12px;
    padding: 0 22px 18px 22px;
}}

#SidebarList {{
    background: transparent;
    border: none;
    outline: none;
    padding: 6px;
}}

#SidebarList::item {{
    padding: 12px 16px;
    margin: 3px 8px;
    border-radius: 10px;
    color: {SUBTEXT};
}}

#SidebarList::item:hover {{
    background-color: {item_hover};
    color: {TEXT};
}}

#SidebarList::item:selected {{
    background-color: {accent};
    color: {CRUST};
    font-weight: 700;
}}

#SidebarFooter {{
    color: {SURFACE2};
    font-size: 11px;
    padding: 10px 22px 18px 22px;
}}

#SidebarSection {{
    color: {OVERLAY};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}}

#PlaylistCombo {{
    background-color: {input_bg};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 8px 10px;
    color: {TEXT};
}}

#PlaylistCombo:hover {{
    border: 1px solid {_shade(accent, 0.85)};
}}

#PlaylistCombo:focus {{
    border: 1px solid {accent};
}}

#PlaylistCombo::drop-down {{
    border: none;
    width: 22px;
}}

#PlaylistCombo QAbstractItemView {{
    background-color: {combo_view};
    border: 1px solid {border};
    border-radius: 8px;
    selection-background-color: {accent};
    selection-color: {CRUST};
    padding: 4px;
}}

#SidebarButton {{
    padding: 8px 10px;
    font-size: 12px;
}}

/* ---------------- Content ---------------- */

#PageTitle {{
    font-size: 20px;
    font-weight: 700;
}}

#PageSubtitle {{
    color: {SUBTEXT};
    font-size: 13px;
}}

#SectionLabel {{
    color: {OVERLAY};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}}

#NowPlaying {{
    font-size: 20px;
    font-weight: 700;
    color: {TEXT};
}}

#NowPlaying[state="ok"] {{
    color: {GREEN};
}}

#NowPlaying[state="error"] {{
    color: {RED};
}}

#SettingsInfo {{
    background-color: {panel_bg};
    border: 1px solid {border};
    border-radius: 12px;
    padding: 16px;
    color: {SUBTEXT};
    font-size: 13px;
}}

#Card {{
    background-color: {panel_bg};
    border: 1px solid {border};
    border-radius: 14px;
    padding: 18px;
}}

#TimeLabel {{
    color: {SUBTEXT};
    font-size: 12px;
}}

/* ---------------- Inputs ---------------- */

QLineEdit, QSpinBox {{
    background-color: {input_bg};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 10px 12px;
    selection-background-color: {accent};
    selection-color: {CRUST};
}}

QLineEdit:focus, QSpinBox:focus {{
    border: 1px solid {accent};
}}

QLineEdit:disabled, QSpinBox:disabled {{
    color: {OVERLAY};
    background-color: {_rgba(SURFACE0, 0.35)};
}}

QSpinBox::up-button, QSpinBox::down-button {{
    width: 16px;
    background: transparent;
    border: none;
}}

QCheckBox {{
    spacing: 8px;
    color: {TEXT};
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 6px;
    border: 1px solid {border};
    background-color: {input_bg};
}}

QCheckBox::indicator:checked {{
    background-color: {accent};
    border: 1px solid {accent};
}}

/* ---------------- Buttons ---------------- */

QPushButton {{
    background-color: {button_bg};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 10px 18px;
    font-weight: 600;
    color: {TEXT};
}}

QPushButton:hover {{
    background-color: {button_hover};
    border: 1px solid {_shade(accent, 0.85)};
}}

QPushButton:pressed {{
    background-color: {button_press};
}}

QPushButton:disabled {{
    color: {OVERLAY};
    background-color: {_rgba(SURFACE0, 0.35)};
    border-color: {_rgba(SURFACE0, 0.4)};
}}

QPushButton#Primary {{
    background-color: {accent};
    color: {CRUST};
    border: none;
}}

QPushButton#Primary:hover {{
    background-color: {accent_hover};
}}

QPushButton#Primary:pressed {{
    background-color: {accent_press};
}}

QPushButton#Primary:disabled {{
    background-color: {_rgba(SURFACE1, 0.6)};
    color: {OVERLAY};
}}

QPushButton#Danger {{
    background-color: {RED};
    color: {CRUST};
    border: none;
}}

QPushButton#Danger:hover {{
    background-color: {_shade(RED, 0.9)};
}}

QPushButton#Transport {{
    font-size: 18px;
    min-width: 48px;
    min-height: 48px;
    padding: 0;
    border-radius: 24px;
}}

QPushButton#TransportPrimary {{
    font-size: 20px;
    min-width: 60px;
    min-height: 60px;
    padding: 0;
    border-radius: 30px;
    background-color: {accent};
    color: {CRUST};
    border: none;
}}

QPushButton#TransportPrimary:hover {{
    background-color: {accent_hover};
}}

QPushButton#ModeToggle {{
    padding: 8px 14px;
    font-size: 13px;
}}

QPushButton#ModeToggle:checked {{
    background-color: {accent};
    color: {CRUST};
    border: none;
}}

QPushButton#ModeToggle:checked:hover {{
    background-color: {accent_hover};
}}

QPushButton#ModeToggle:disabled {{
    color: {OVERLAY};
    background-color: {_rgba(SURFACE0, 0.35)};
    border-color: {_rgba(SURFACE0, 0.4)};
}}

/* ---------------- Lists ---------------- */

QListWidget {{
    background-color: {list_bg};
    border: 1px solid {border};
    border-radius: 12px;
    padding: 6px;
    outline: none;
}}

QListWidget::item {{
    padding: 10px 12px;
    border-radius: 8px;
    color: {TEXT};
}}

QListWidget::item:hover {{
    background-color: {item_hover};
}}

QListWidget::item:selected {{
    background-color: {accent};
    color: {CRUST};
}}

/* ---------------- Progress / Sliders ---------------- */

QProgressBar {{
    background-color: {_rgba(SURFACE0, 0.6)};
    border: none;
    border-radius: 5px;
    height: 10px;
    text-align: center;
}}

QProgressBar::chunk {{
    border-radius: 5px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {accent}, stop:1 {_shade(accent, 1.25)});
}}

QSlider::groove:horizontal {{
    height: 6px;
    background: {_rgba(SURFACE0, 0.7)};
    border-radius: 3px;
}}

QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {accent}, stop:1 {_shade(accent, 1.25)});
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: {TEXT};
    width: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}

QSlider::handle:horizontal:hover {{
    background: {accent};
}}

#SeekBar {{
    min-height: 18px;
}}

#SeekBar::groove:horizontal {{
    height: 8px;
    border-radius: 4px;
}}

#SeekBar::sub-page:horizontal {{
    border-radius: 4px;
}}

#SeekBar::handle:horizontal {{
    width: 16px;
    margin: -4px 0;
    border-radius: 8px;
}}

/* ---------------- Misc ---------------- */

QStatusBar {{
    background-color: {_rgba(CRUST, 0.9)};
    color: {SUBTEXT};
}}

QStatusBar::item {{
    border: none;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 4px;
}}

QScrollBar::handle:vertical {{
    background: {_rgba(SURFACE1, 0.8)};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {accent};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QToolTip {{
    background-color: {CRUST};
    color: {TEXT};
    border: 1px solid {accent};
    border-radius: 6px;
    padding: 6px 8px;
}}

#Status {{
    color: {SUBTEXT};
    font-size: 13px;
}}

#Status[state="ok"] {{
    color: {GREEN};
}}

#Status[state="error"] {{
    color: {RED};
}}

#Status[state="busy"] {{
    color: {YELLOW};
}}
"""


# ----------------------------------------------------------------------
# Application helpers
# ----------------------------------------------------------------------

def apply_theme(app, accent=None, glass=None):
    """Apply the Fusion style, base font and the generated stylesheet.

    When ``accent`` or ``glass`` are omitted the saved preferences are used.
    """

    if accent is None or glass is None:
        saved_accent, saved_glass = settings.read_appearance()

        if accent is None:
            accent = saved_accent

        if glass is None:
            glass = saved_glass

    app.setStyle("Fusion")
    app.setFont(QFont("Inter", 10))
    app.setStyleSheet(build_stylesheet(accent, glass))


def set_appearance(accent=None, glass=None):
    """Re-apply the theme live using the running application instance."""

    app = QApplication.instance()

    if app is None:
        return

    apply_theme(app, accent=accent, glass=glass)
