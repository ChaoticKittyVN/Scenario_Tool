"""
Ren'Py Transition Generator
生成转场命令
"""
from core.base_sentence_generator import BaseSentenceGenerator


class TransitionGenerator(BaseSentenceGenerator):
    """转场生成器"""

    param_config = {
        "UseTrans": {},
        "TransWith": {
            "translate_type": "Transition",
            "format": "with {value}",
            "default": "Dissolve"
            },
        "TransWithAtr": {
            "format": "({value})",
            "default": "1.0"
        },
    }

    @property
    def category(self):
        return "Transition"

    @property
    def priority(self) -> int:
        return 400

    def process(self, data):
        """
        处理转场参数

        Args:
            data: 参数字典

        Returns:
            List[str]: 生成的转场命令
        """
        if not self.can_process(data):
            return None

        data = self.do_translate(data)

        transition = self.get_sentence("TransWith", data, use_default=True)

        atr = self.get_sentence("TransWithAtr", data, use_default=True)

        line = f"{transition}{atr}"

        return [line]