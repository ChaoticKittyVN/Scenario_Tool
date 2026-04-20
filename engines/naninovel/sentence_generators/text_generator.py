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
        "PrinterPos": {},
        "Transition": {},
        "TransitionSub": {}
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
        printer_status = self.get_value("PrinterStatus", data)

        transition = self.get_value("Transition", data)
        transition_sub = self.get_value("TransitionSub", data)
    
        lines = []
        # 处理打印机设置

        printer_show = "@printer"

        if printer_status != WindowMode.HIDE.value:
            if printer in [WindowMode.SHOW.value, WindowMode.SHOW_AND_HIDE.value] or printer or (transition in ["局部转场", "新场景", "立绘转场"] and transition_sub not in ["过渡", "开始"]):
                printer = self.translator.translate('Printer', printer)
                if self.exists_param("Printer", data):
                    printer_show += f" {self.translator.translate('Printer', printer)}"

                printer_pos = self.get_sentence("PrinterPos", data)
                if printer_pos:
                    printer_show += printer_pos
                lines.append(printer_show)             
            else:
                pass

        # 处理对话文本
        if character_name:
            if character_name in self.SPECIAL_NAME_VALUES:
                if character_name == SpecialName.NANINOVEL_COMMAND.value:
                    # 直接输入 Naninovel 命令
                    lines.append(text)
                elif character_name == SpecialName.LABEL_COMMAND.value:
                    lines.append(f"# {text}")
                elif character_name == SpecialName.JUMP_COMMAND.value:
                    lines.append(f"@goto {text}")
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
