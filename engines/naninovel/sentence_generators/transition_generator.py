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
    
        "TransitionDissolve": {
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

        lines = []

        transition = self.get_value('Transition', data)
        time = self.get_sentence('TransitionTime', data, use_default=True)
        if self.exists_param("TransitionDissolve", data):
            dissolve = self.get_sentence("TransitionDissolve", data)
        else:
            dissolve = ""

        lines.append(f"@trans{dissolve}{time}")

        if transition == "PartTransOnly":
            return lines

        lines.append("    @hideAll")

        if transition == "PartTransNew":
            return lines

        lines.append(f'    {self.get_sentence("Transition", data)}')

        if self.exists_param("TransitionWaitPause", data):
            pause = self.get_value("TransitionWaitPause", data)
            if pause.startswith("i") or float(pause) > 0:
                lines.append(self.get_sentence("TransitionWaitPause", data))
            else:
                pass
        else:
            lines.append(self.get_sentence("TransitionWaitPause", data, use_default=True))

        return lines

