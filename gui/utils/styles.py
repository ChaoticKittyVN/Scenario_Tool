"""System-aware GUI theme construction."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication


LIGHT_COLORS = {
    "window": "#f4f5f7",
    "surface": "#ffffff",
    "surface_alt": "#f7f8fa",
    "text": "#202124",
    "muted": "#68707a",
    "border": "#d7dbe0",
    "primary": "#276ef1",
    "primary_hover": "#1f5ccc",
    "primary_pressed": "#1749a8",
    "selection": "#e8f0fe",
    "selection_text": "#174ea6",
    "secondary": "#eef0f3",
    "secondary_hover": "#e1e4e8",
    "disabled": "#dfe2e6",
    "disabled_text": "#8a9099",
    "success": "#238636",
    "success_bg": "#e6f4ea",
    "success_border": "#b7dfc5",
}

DARK_COLORS = {
    "window": "#17191c",
    "surface": "#202328",
    "surface_alt": "#181b1f",
    "text": "#eef0f3",
    "muted": "#a8adb5",
    "border": "#3a3f46",
    "primary": "#5b8def",
    "primary_hover": "#78a2f2",
    "primary_pressed": "#3f70cf",
    "selection": "#263b64",
    "selection_text": "#d6e4ff",
    "secondary": "#2a2e34",
    "secondary_hover": "#353a42",
    "disabled": "#30343a",
    "disabled_text": "#767d87",
    "success": "#7ee787",
    "success_bg": "#173d25",
    "success_border": "#2f6b42",
}


def build_style(dark: bool) -> str:
    colors = DARK_COLORS if dark else LIGHT_COLORS
    return f"""
QMainWindow, QWidget {{
    color: {colors['text']};
    background-color: {colors['window']};
}}

QTabWidget::pane {{
    border: 1px solid {colors['border']};
    background-color: {colors['surface']};
    border-radius: 4px;
}}

QTabBar::tab {{
    color: {colors['muted']};
    background-color: {colors['secondary']};
    border: 1px solid {colors['border']};
    border-bottom: none;
    padding: 8px 20px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}}

QTabBar::tab:selected {{
    color: {colors['primary']};
    background-color: {colors['surface']};
    font-weight: bold;
}}

QTabBar::tab:hover {{
    background-color: {colors['secondary_hover']};
}}

QGroupBox {{
    color: {colors['text']};
    font-weight: bold;
    border: 1px solid {colors['border']};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 10px;
    background-color: {colors['surface']};
}}

QGroupBox::title {{
    color: {colors['primary']};
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
}}

QPushButton {{
    color: #ffffff;
    background-color: {colors['primary']};
    border: 1px solid {colors['primary']};
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: bold;
}}

QPushButton:hover {{ background-color: {colors['primary_hover']}; }}
QPushButton:pressed {{ background-color: {colors['primary_pressed']}; }}
QPushButton:disabled {{
    color: {colors['disabled_text']};
    background-color: {colors['disabled']};
    border-color: {colors['disabled']};
}}

QPushButton#iconButton,
QPushButton#secondaryButton {{
    color: {colors['text']};
    background-color: {colors['secondary']};
    border-color: {colors['border']};
}}

QPushButton#iconButton:hover,
QPushButton#secondaryButton:hover {{
    background-color: {colors['secondary_hover']};
}}

QLineEdit, QComboBox, QSpinBox {{
    color: {colors['text']};
    background-color: {colors['surface']};
    border: 1px solid {colors['border']};
    border-radius: 4px;
    padding: 6px 10px;
    selection-background-color: {colors['selection']};
    selection-color: {colors['selection_text']};
}}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 2px solid {colors['primary']};
}}

QLineEdit:disabled, QComboBox:disabled {{
    color: {colors['disabled_text']};
    background-color: {colors['disabled']};
}}

QComboBox QAbstractItemView {{
    color: {colors['text']};
    background-color: {colors['surface']};
    border: 1px solid {colors['border']};
    selection-background-color: {colors['selection']};
    selection-color: {colors['selection_text']};
    outline: 0;
}}

QComboBox QAbstractItemView::item {{ padding: 6px 10px; }}

QCheckBox {{
    color: {colors['text']};
    spacing: 8px;
    background-color: transparent;
}}

QTextEdit, QPlainTextEdit, QTextBrowser, QListWidget {{
    color: {colors['text']};
    background-color: {colors['surface_alt']};
    border: 1px solid {colors['border']};
    border-radius: 4px;
    selection-background-color: {colors['selection']};
    selection-color: {colors['selection_text']};
}}

QTextEdit, QPlainTextEdit, QTextBrowser {{
    font-family: "Consolas", "Microsoft YaHei UI", monospace;
    font-size: 9pt;
}}

QListWidget {{
    background-color: {colors['surface']};
    padding: 4px;
}}

QListWidget::item {{ min-height: 28px; padding: 5px 8px; }}
QListWidget::item:selected {{
    color: {colors['selection_text']};
    background-color: {colors['selection']};
    border-radius: 3px;
}}

QScrollArea, QScrollArea > QWidget > QWidget,
QWidget#toolPanel, QWidget#argumentContainer {{
    color: {colors['text']};
    background-color: {colors['surface']};
}}

QScrollArea {{
    border: 1px solid {colors['border']};
    border-radius: 4px;
}}

QProgressBar {{
    color: {colors['text']};
    border: 1px solid {colors['border']};
    border-radius: 4px;
    text-align: center;
    background-color: {colors['surface_alt']};
}}

QProgressBar::chunk {{ background-color: {colors['success']}; border-radius: 3px; }}
QLabel {{ color: {colors['text']}; background-color: transparent; }}
QLabel#pageTitle {{ color: {colors['text']}; font-size: 16pt; font-weight: bold; }}
QLabel#sectionTitle {{ color: {colors['text']}; font-size: 11pt; font-weight: bold; }}
QLabel#mutedLabel {{ color: {colors['muted']}; }}
QLabel#statusBadge {{
    color: {colors['success']};
    background-color: {colors['success_bg']};
    border: 1px solid {colors['success_border']};
    border-radius: 4px;
    padding: 3px 7px;
}}

QStatusBar {{
    color: {colors['muted']};
    background-color: {colors['window']};
    border-top: 1px solid {colors['border']};
}}
"""


def system_uses_dark_theme(app: QApplication) -> bool:
    scheme = app.styleHints().colorScheme()
    if scheme == Qt.ColorScheme.Dark:
        return True
    if scheme == Qt.ColorScheme.Light:
        return False
    window_color = app.palette().color(QPalette.ColorRole.Window)
    return window_color.lightness() < 128


def apply_system_theme(app: QApplication) -> None:
    def update_theme(*_args) -> None:
        app.setStyleSheet(build_style(system_uses_dark_theme(app)))

    app._scenario_theme_callback = update_theme
    app.styleHints().colorSchemeChanged.connect(update_theme)
    update_theme()
