"""
Ren'Py Text Generator
生成文本和对话命令
"""
from core.base_sentence_generator import BaseSentenceGenerator
from core.constants import WindowMode, SpecialSpeaker


class TextGenerator(BaseSentenceGenerator):
    """文本生成器"""

    param_config = {
        "Window": {
            "translate_type": "Window"
        },
        "Speaker": {
            "translate_type": "Speaker",
        },
        "Text": {},
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
        window = self.get_value("Window", data)

        lines = []

        # 处理窗口显示
        if window in [WindowMode.SHOW.value, WindowMode.SHOW_AND_HIDE.value]:
            lines.append("window show")

        # 处理对话文本
        if speaker:
            if speaker == SpecialSpeaker.RENPY_COMMAND.value:
                # 直接输入 Ren'Py 命令
                lines.append(text)
            else:
                speaker = self.translator.translate("Speaker", speaker)
                lines.append(f'{speaker} "{text}"')
        else:
            if text:
                lines.append(f'"{text}"')

        # 处理窗口隐藏
        if window in [WindowMode.HIDE.value, WindowMode.SHOW_AND_HIDE.value]:
            lines.append("window hide")

        return lines
