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
        "HidePrinter": ,
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

        speaker = data.get("Speaker")
        text = data.get("Text")
        printer = data.get("Printer")
        hide_printer = data.get("HidePrinter")

        results = []

        # 处理打印机设置
        if printer:
            printer = self.translator.translate("Printer", printer)
            printer_pos = data.get("PrinterPos")
            temp = f"@printer {printer}"
            if printer_pos:
                temp += f" pos:{printer_pos}"
            results.append(temp)

        # 处理对话文本
        if speaker:
            if speaker == SpecialSpeaker.NANINOVEL_COMMAND.value:
                # 直接输入 Naninovel 命令
                results.append(text)
            else:
                speaker = self.translator.translate("Speaker", speaker)
                results.append(f'{speaker}: {text}')
        else:
            if text:
                results.append(text)

        # 处理隐藏打印机
        if hide_printer:
            results.append("@hidePrinter")

        return results
