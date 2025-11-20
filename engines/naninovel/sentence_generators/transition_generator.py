"""
Naninovel Transition Generator
生成转场命令
"""
from core.base_sentence_generator import BaseSentenceGenerator


class TransitionGenerator(BaseSentenceGenerator):
    """转场生成器"""

    param_config = {
        "Transition": {
            "translate_type": "Transition"
        }
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

        transition = data.get("Transition")
        if not transition:
            return []

        result = f"@transition {transition}"
        return [result]
