"""
Naninovel Text Generator
生成文本和对话命令
"""
from core.base_sentence_generator import BaseSentenceGenerator
from core.constants import SpecialSpeaker


class TextGenerator(BaseSentenceGenerator):
    """文本生成器"""

    param_config = {
        "Speaker": {
            "translate_type": "Speaker"
        },
        "Text": {},
        "Printer": {
            "translate_type": "Printer"
        },
        "PrinterPos": {}
    }

    @property
    def category(self):
        return "Text"

    @property
    def priority(self) -> int:
        return 900

    def process(self, data):
        """
        处理文本参数

        Args:
            data: 参数字典

        Returns:
            List[str]: 生成的文本命令
        """
        if not self.can_process(data):
            return None

        speaker = self.get_value("Speaker", data)
        text = self.get_value("Text", data)
        printer = self.get_value("Printer", data)

        lines = []

        # 处理打印机设置
        if printer != "隐藏":
            printer = self.translator.translate("Printer", printer)
            printer_pos = self.get_sentence("PrinterPos", data)
            line = f"@printer {printer}"
            if printer_pos:
                line += printer_pos
            lines.append(line)
        else:
            lines.append("@hidePrinter wait:true")

        # 处理对话文本
        if speaker:
            if speaker == SpecialSpeaker.NANINOVEL_COMMAND.value:
                # 直接输入 Naninovel 命令
                lines.append(text)
            else:
                speaker = self.translator.translate("Speaker", speaker)
                lines.append(f'{speaker}: {text}')
        else:
            if text:
                lines.append(text)

        return lines
