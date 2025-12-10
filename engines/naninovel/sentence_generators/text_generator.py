"""
Naninovel Text Generator
生成文本和对话命令
"""
from core.base_sentence_generator import BaseSentenceGenerator
from core.constants import WindowMode, SpecialName


class TextGenerator(BaseSentenceGenerator):
    """文本生成器"""

    param_config = {
        "Name": {
            "validate_type": "Name"
        },
        "Text": {},
        "Printer": {
            "validate_type": "Printer"
        },
        "PrinterPos": {}
    }

    SPECIAL_NAME_VALUES = {member.value for member in SpecialName}

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

        character_name = self.get_value("Name", data)
        text = self.get_value("Text", data)
        printer = self.get_value("Printer", data)

        lines = []
        # 处理打印机设置
        if printer != WindowMode.HIDE.value and printer:
            if printer in [WindowMode.SHOW.value, WindowMode.SHOW_AND_HIDE.value]:
                line = f"@printer"
            else:
                printer = self.translator.translate('Printer', printer)
                printer_pos = self.get_sentence("PrinterPos", data)
                line = f"@printer {printer}"
                if printer_pos:
                    line += printer_pos
            lines.append(line)

        # 处理对话文本
        if character_name:
            if character_name in self.SPECIAL_NAME_VALUES:
                if character_name == SpecialName.NANINOVEL_COMMAND.value:
                    # 直接输入 Naninovel 命令
                    lines.append(text)
                elif character_name == SpecialName.LABEL_CAMMAND.value:
                    lines.append(f"# {text}")
                else:
                    raise ValueError(f"不支持的特殊说话者：{character_name}。")
            else:
                # character_name = self.translator.translate("Name", character_name)
                lines.append(f'{character_name}: {text}')
        else:
            if text:
                lines.append(text)

        if printer in [WindowMode.HIDE.value, WindowMode.SHOW_AND_HIDE.value]:
            lines.append("@hidePrinter wait:true")

        return lines
