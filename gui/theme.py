"""Dark theme and global styling for the EchoYT desktop GUI."""

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

FONT_STACK = '"Inter", "Segoe UI", "Ubuntu", "Noto Sans", "Cantarell", sans-serif'

DARK_QSS = f"""
* {{
    font-family: {FONT_STACK};
}}

QWidget {{
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-size: 14px;
}}

QMainWindow, QDialog {{
    background-color: #181825;
}}

/* ---------------- Sidebar ---------------- */

#Sidebar {{
    background-color: #11111b;
    border-right: 1px solid #313244;
}}

#AppTitle {{
    font-size: 22px;
    font-weight: 800;
    color: #cdd6f4;
    padding: 24px 22px 2px 22px;
}}

#AppSubtitle {{
    color: #6c7086;
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
    color: #a6adc8;
}}

#SidebarList::item:hover {{
    background-color: #1e1e2e;
    color: #cdd6f4;
}}

#SidebarList::item:selected {{
    background-color: #89b4fa;
    color: #11111b;
    font-weight: 700;
}}

#SidebarFooter {{
    color: #585b70;
    font-size: 11px;
    padding: 10px 22px 18px 22px;
}}

#SidebarSection {{
    color: #6c7086;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}}

#PlaylistCombo {{
    background-color: #1e1e2e;
    border: 1px solid #45475a;
    border-radius: 8px;
    padding: 8px 10px;
    color: #cdd6f4;
}}

#PlaylistCombo:hover {{
    border: 1px solid #585b70;
}}

#PlaylistCombo::drop-down {{
    border: none;
    width: 22px;
}}

#PlaylistCombo QAbstractItemView {{
    background-color: #1e1e2e;
    border: 1px solid #45475a;
    border-radius: 8px;
    selection-background-color: #89b4fa;
    selection-color: #11111b;
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
    color: #a6adc8;
    font-size: 13px;
}}

#SectionLabel {{
    color: #6c7086;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}}

#NowPlaying {{
    font-size: 20px;
    font-weight: 700;
    color: #cdd6f4;
}}

#NowPlaying[state="ok"] {{
    color: #a6e3a1;
}}

#NowPlaying[state="error"] {{
    color: #f38ba8;
}}

#SettingsInfo {{
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 12px;
    padding: 16px;
    color: #a6adc8;
    font-size: 13px;
}}

#TimeLabel {{
    color: #a6adc8;
    font-size: 12px;
}}

/* ---------------- Inputs ---------------- */

QLineEdit, QSpinBox {{
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 10px;
    padding: 10px 12px;
    selection-background-color: #89b4fa;
    selection-color: #11111b;
}}

QLineEdit:focus, QSpinBox:focus {{
    border: 1px solid #89b4fa;
}}

QLineEdit:disabled, QSpinBox:disabled {{
    color: #6c7086;
    background-color: #292938;
}}

QSpinBox::up-button, QSpinBox::down-button {{
    width: 16px;
    background: transparent;
    border: none;
}}

/* ---------------- Buttons ---------------- */

QPushButton {{
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 10px;
    padding: 10px 18px;
    font-weight: 600;
    color: #cdd6f4;
}}

QPushButton:hover {{
    background-color: #45475a;
}}

QPushButton:pressed {{
    background-color: #585b70;
}}

QPushButton:disabled {{
    color: #6c7086;
    background-color: #292938;
    border-color: #313244;
}}

QPushButton#Primary {{
    background-color: #89b4fa;
    color: #11111b;
    border: none;
}}

QPushButton#Primary:hover {{
    background-color: #74a0ea;
}}

QPushButton#Primary:pressed {{
    background-color: #5f8de0;
}}

QPushButton#Primary:disabled {{
    background-color: #45475a;
    color: #6c7086;
}}

QPushButton#Danger {{
    background-color: #f38ba8;
    color: #11111b;
    border: none;
}}

QPushButton#Danger:hover {{
    background-color: #eb7aa0;
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
    background-color: #89b4fa;
    color: #11111b;
    border: none;
}}

QPushButton#TransportPrimary:hover {{
    background-color: #74a0ea;
}}

/* ---------------- Lists ---------------- */

QListWidget {{
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 12px;
    padding: 6px;
    outline: none;
}}

QListWidget::item {{
    padding: 10px 12px;
    border-radius: 8px;
    color: #cdd6f4;
}}

QListWidget::item:hover {{
    background-color: #313244;
}}

QListWidget::item:selected {{
    background-color: #89b4fa;
    color: #11111b;
}}

/* ---------------- Progress / Sliders ---------------- */

QProgressBar {{
    background-color: #313244;
    border: none;
    border-radius: 5px;
    height: 10px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: #89b4fa;
    border-radius: 5px;
}}

QSlider::groove:horizontal {{
    height: 6px;
    background: #313244;
    border-radius: 3px;
}}

QSlider::sub-page:horizontal {{
    background: #89b4fa;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: #cdd6f4;
    width: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}

/* ---------------- Misc ---------------- */

QStatusBar {{
    background-color: #11111b;
    color: #a6adc8;
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
    background: #45475a;
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: #585b70;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

#Status {{
    color: #a6adc8;
    font-size: 13px;
}}

#Status[state="ok"] {{
    color: #a6e3a1;
}}

#Status[state="error"] {{
    color: #f38ba8;
}}

#Status[state="busy"] {{
    color: #f9e2af;
}}
"""


def apply_theme(app: QApplication):
    """Apply the Fusion style, base font and dark stylesheet."""

    app.setStyle("Fusion")
    app.setFont(QFont("Inter", 10))
    app.setStyleSheet(DARK_QSS)
