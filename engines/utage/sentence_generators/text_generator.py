"""
Utage Text Generator
生成文本和对话命令
"""
from core.base_sentence_generator import BaseSentenceGenerator
from core.constants import WindowMode, SpecialName


class TextGenerator(BaseSentenceGenerator):
    """文本生成器"""

    param_config = {
        "Name": {
            "translate_type": "Name",
        },
        "Text": {},
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
            List[Dict[Str, Any]]: 生成的文本命令
        """
        if not self.can_process(data):
            return None

        character_name = self.get_value("Name", data)
        text = self.get_value("Text", data)

        lines = []

        # 处理对话文本
        if character_name:
            # if character_name in self.SPECIAL_NAME_VALUES:
            #     # elif character_name == SpecialName.LABEL_CAMMAND.value:
            #     #     lines.append(f"label {text}:")
            #     # else:
            #     #     raise ValueError(f"不支持的特殊说话者：{character_name}。")
            # else:
                # character_name = self.translator.translate("Name", character_name)
                lines.append({
                     "Arg2": character_name,
                     "Text": text
                }
                             )
        else:
            if text:
                lines.append(
                    {"Text": text}
                )

        return lines
