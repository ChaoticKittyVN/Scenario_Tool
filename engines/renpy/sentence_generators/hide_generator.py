"""
Ren'Py Hide Generator
生成隐藏命令
"""
from core.base_sentence_generator import BaseSentenceGenerator


class HideGenerator(BaseSentenceGenerator):
    """隐藏生成器"""

    param_config = {
        "Hide": {
            "translate_types": ["Character", "Background", "Event"]
        },
        "HideWith": {
            "translate_type": "Transition",
            "format": " with {value}"
        }
    }

    @property
    def category(self):
        return "Hide"

    @property
    def priority(self) -> int:
        return 300

    def process(self, data):
        """
        处理隐藏参数

        Args:
            data: 参数字典

        Returns:
            List[str]: 生成的隐藏命令
        """
        if not self.can_process(data):
            return None

        data = self.do_translate(data)

        hide_target = self.get_value("Hide", data)
        if not hide_target:
            return []

        transition = self.get_sentence("HideWith", data)
        result = f"hide {hide_target}{transition}"
        return [result]
