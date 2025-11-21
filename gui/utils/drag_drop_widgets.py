"""
支持拖拽的自定义控件
"""
from pathlib import Path
from PySide6.QtWidgets import QLineEdit
from PySide6.QtCore import Qt


class DragDropLineEdit(QLineEdit):
    """支持拖拽文件夹的 QLineEdit"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """拖拽放下事件"""
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if Path(path).is_dir():
                self.setText(path)
                event.acceptProposedAction()
            else:
                event.ignore()
