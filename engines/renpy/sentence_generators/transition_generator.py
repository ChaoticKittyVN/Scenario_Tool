"""
Ren'Py Transition Generator
生成转场命令
"""
from core.base_sentence_generator import BaseSentenceGenerator


class TransitionGenerator(BaseSentenceGenerator):
    """转场生成器"""

    param_config = {
        "UseTrans": {},
        "TransScene": {
            "translate_type": "TransScene",
        },
        "TransSub": {
            "validate_type": "TransSub"
        },
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

        line = ""

        transition = self.get_sentence("TransWith", data, use_default=True)

        atr = self.get_sentence("TransWithAtr", data, use_default=True)

        trans = self.get_value("TransScene", data)

        trans_sub = self.get_value("TransSub", data)

        if trans not in ["局部转场", "立绘转场", "新场景", "转场组件"] and trans_sub not in ["过渡"]:
            if trans in ["black", "white"]:
                line = f"scene {trans} {transition}{atr}"
        elif trans_sub not in ["开始"] and trans not in ["转场组件"]:
            if trans in ["局部转场", "立绘转场"] and not self.exists_param("TransWithAtr", data):
                atr = "(0.5)"
            line = f"{transition}{atr}"

        return [line] if line else None