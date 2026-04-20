"""
Naninovel Transition Generator
生成转场命令
"""
from core.base_sentence_generator import BaseSentenceGenerator


class TransitionGenerator(BaseSentenceGenerator):
    """转场生成器"""

    param_config = {
        "Transition": {
            "translate_type": "Transition",
            "format": "    @back {value} id:转场"
        },

        "TransitionSub": {
            "validate_type": "TransitionSub",
        },

    
        "TransitionDissolve": {
            "translate_type": "Dissolve",
            "format": " Custom dissolve:Rule/{value} params:95"
        },

        "TransitionTime": {
            "format": " time:{value}",
            "default": "1.0",
        },

        "TransitionWaitPause": {
            "format": "@wait {value}",
            "default": "i1",
        },
        "Printer": {}
    }

    @property
    def category(self):
        return "Transition"

    @property
    def priority(self) -> int:
        return 120


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

        lines = []

        transition = self.get_value('Transition', data)
        transition_sub = self.get_value('TransitionSub', data)

        if self.exists_param("TransitionTime", data):
            time = self.get_sentence('TransitionTime', data)
        elif transition in ["PartTrans", "CharTrans"]:
            time = " time:0.5"
        else:
            time = self.get_sentence('TransitionTime', data, use_default=True)

        if self.exists_param("TransitionDissolve", data):
            dissolve = self.get_sentence("TransitionDissolve", data)
        else:
            dissolve = ""

        if not self.exists_param("Printer", data) and transition in ["PartTrans", "NewScene", "CharTrans"] and transition_sub not in ["过渡", "开场"]:
            lines.append("@hidePrinter wait:true")

        lines.append(f"@trans{dissolve}{time}")

        if transition in ["PartTrans", "CharTrans"]:
            if transition in ["CharTrans"]:
                lines.append("    @hideChars")
            return lines

        lines.append("    @hideAll")

        if transition in ["NewScene"]:
            return lines

        lines.append(self.get_sentence("Transition", data))

        if self.exists_param("TransitionWaitPause", data):
            pause = self.get_value("TransitionWaitPause", data)
            if pause.startswith("i") or float(pause) > 0:
                lines.append(self.get_sentence("TransitionWaitPause", data))
            else:
                pass
        else:
            lines.append(self.get_sentence("TransitionWaitPause", data, use_default=True))

        return lines

    def can_process(self, data: dict) -> bool:
        """判断是否可以处理转场参数"""
        return self.exists_param("Transition", data) and self.get_value("Transition", data) not in ["转场组件"] and self.get_value("TransitionSub", data) not in ["结束"]