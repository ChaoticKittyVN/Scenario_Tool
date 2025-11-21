"""
GUI 样式定义
"""

MODERN_STYLE = """
/* 全局样式 */
QMainWindow {
    background-color: #f5f5f5;
}

/* 标签页样式 */
QTabWidget::pane {
    border: 1px solid #dcdcdc;
    background-color: white;
    border-radius: 4px;
}

QTabBar::tab {
    background-color: #e8e8e8;
    color: #333;
    padding: 8px 20px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: white;
    color: #2196F3;
    font-weight: bold;
}

QTabBar::tab:hover {
    background-color: #f0f0f0;
}

/* 分组框样式 */
QGroupBox {
    font-weight: bold;
    border: 1px solid #dcdcdc;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 10px;
    background-color: white;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #2196F3;
}

/* 按钮样式 */
QPushButton {
    background-color: #2196F3;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #1976D2;
}

QPushButton:pressed {
    background-color: #0D47A1;
}

QPushButton:disabled {
    background-color: #BDBDBD;
    color: #757575;
}

/* 小按钮（浏览、恢复默认） */
QPushButton[objectName*="btn"]:!pressed {
    background-color: #757575;
}

QPushButton[objectName*="btn"]:hover {
    background-color: #616161;
}

QPushButton[objectName*="reset"] {
    background-color: #FF9800;
}

QPushButton[objectName*="reset"]:hover {
    background-color: #F57C00;
}

/* 输入框样式 */
QLineEdit {
    border: 1px solid #dcdcdc;
    border-radius: 4px;
    padding: 6px 10px;
    background-color: white;
}

QLineEdit:focus {
    border: 2px solid #2196F3;
}

QLineEdit:disabled {
    background-color: #f5f5f5;
    color: #9e9e9e;
}

/* 下拉框样式 */
QComboBox {
    border: 1px solid #dcdcdc;
    border-radius: 4px;
    padding: 6px 10px;
    background-color: white;
}

QComboBox:focus {
    border: 2px solid #2196F3;
}

QComboBox QAbstractItemView {
    border: 1px solid #dcdcdc;
    background-color: white;
    selection-background-color: #E3F2FD;
    selection-color: #1976D2;
    outline: 0;
}

QComboBox QAbstractItemView::item {
    padding: 6px 10px;
}

QComboBox QAbstractItemView::item:selected {
    background-color: #E3F2FD;
    color: #1976D2;
    outline: 0;
}

/* 复选框样式 */
QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #dcdcdc;
    border-radius: 3px;
    background-color: white;
}

QCheckBox::indicator:checked {
    background-color: #2196F3;
    border-color: #2196F3;
    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEgNEw0LjUgNy41TDExIDEiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+PC9zdmc+);
}

/* 文本编辑框（日志）样式 */
QTextEdit {
    border: 1px solid #dcdcdc;
    border-radius: 4px;
    background-color: #fafafa;
    font-family: "Consolas", "Monaco", monospace;
    font-size: 9pt;
}

/* 进度条样式 */
QProgressBar {
    border: 1px solid #dcdcdc;
    border-radius: 4px;
    text-align: center;
    background-color: #f5f5f5;
}

QProgressBar::chunk {
    background-color: #4CAF50;
    border-radius: 3px;
}

/* 标签样式 */
QLabel {
    color: #424242;
}

/* 状态栏样式 */
QStatusBar {
    background-color: #f5f5f5;
    color: #616161;
    border-top: 1px solid #dcdcdc;
}
"""
