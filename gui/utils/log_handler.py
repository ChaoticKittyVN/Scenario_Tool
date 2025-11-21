"""
GUI 日志处理器
将日志输出到 GUI 文本框
"""
import logging
import re
from PySide6.QtCore import QObject, Signal


class QTextEditLogger(logging.Handler, QObject):
    """将日志输出到 QTextEdit 的处理器"""

    log_signal = Signal(str)

    # ANSI 到 HTML 颜色映射
    ANSI_COLORS = {
        '30': 'black', '31': 'red', '32': 'green', '33': 'orange',
        '34': 'blue', '35': 'magenta', '36': 'cyan', '37': 'white',
    }

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def _ansi_to_html(self, text):
        """将 ANSI 颜色代码转换为 HTML"""
        # 处理加粗和颜色的组合 \x1b[1m\x1b[XXm
        text = re.sub(r'\x1b\[1m\x1b\[(\d+)m', lambda m: f'<b><span style="color: {self.ANSI_COLORS.get(m.group(1), "black")};">', text)

        # 处理单独的加粗标记
        text = re.sub(r'\x1b\[1m', '<b>', text)

        # 处理单独的颜色代码
        for code, color in self.ANSI_COLORS.items():
            text = re.sub(rf'\x1b\[{code}m', f'<span style="color: {color};">', text)

        # 处理重置标记
        text = re.sub(r'\x1b\[0m', '</span></b>', text)

        return text

    def emit(self, record):
        """发送日志记录"""
        msg = self.format(record)
        # 转换 ANSI 颜色代码为 HTML
        html_msg = self._ansi_to_html(msg)
        self.log_signal.emit(html_msg)
