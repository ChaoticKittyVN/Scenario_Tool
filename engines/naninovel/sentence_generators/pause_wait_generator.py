from core.base_sentence_generator import BaseSentenceGenerator

class PauseWaitGenerator(BaseSentenceGenerator):
    """等待时间生成器"""


    param_config = {
        "WaitPause": {
            "format": "@wait {value}"
        },
        "TransitionWaitPause": {
            "format": "@wait {value}"
        },
        "Transition": {},
        "TransitionSub": {}
    }

    @property
    def category(self):
        return "Pause"

    @property
    def priority(self) -> int:
        return 850
    
    def process(self, data):
        """
        处理等待参数

        Args:
            data: 参数字典

        Returns:
            List[str]: 生成的注释命令
        """
        if not self.can_process(data):
            return None

        lines = []

        transition = self.get_value("Transition", data)
        transition_sub = self.get_value("TransitionSub", data)

        if transition in ["新场景", "局部转场", "立绘转场"] and transition_sub not in ["开始"]:
            if self.exists_param("TransitionWaitPause", data):
                pause = self.get_value("TransitionWaitPause", data)
                if pause.startswith("i") or float(pause) > 0:
                    lines.append(self.get_sentence("TransitionWaitPause", data))
                else:
                    pass
            elif transition in ["局部转场", "立绘转场"]:
                lines.append("@wait i0.5")
            elif transition in ["新场景"]:
                lines.append("@wait i1")

        wait = self.get_sentence("WaitPause", data)

        if wait: 
            lines.append(wait)

        return lines