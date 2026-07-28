"""
Ren'Py Pause Generator
生成暂停命令
"""
from core.base_sentence_generator import BaseSentenceGenerator


class PauseGenerator(BaseSentenceGenerator):
    """暂停生成器"""

    param_config = {
        "Pause": {},
        "TransScene": {},
        "TransSub": {},
        "TransPause": {},
    }

    @property
    def category(self):
        return "Pause"

    @property
    def priority(self) -> int:
        return 500

    def process(self, data):
        """
        处理暂停参数

        Args:
            data: 参数字典

        Returns:
            List[str]: 生成的暂停命令
        """
        if not self.can_process(data):
            return None

        lines = []

        trans = self.get_value("TransScene", data)
        trans_sub = self.get_value("TransSub", data)

        trans_pause = self.get_value("TransPause", data)

        if trans_pause:
            lines.append(f"pause {trans_pause}")
        elif trans_sub not in ["开始"]:
            if trans in ["局部转场", "立绘转场"]:
                lines.append("pause 0.5")
            elif trans in ["新场景", "转黑", "转白"]:
                lines.append("pause 1.0")

        if not self.exists_param("Pause", data):
            return lines

        pause = self.get_value("Pause", data)

        if pause == "hard":
            lines.append("pause")
        else:
            try:
                pause_time = float(pause)
                lines.append(f"pause {pause_time}")
            except ValueError:
                lines.append("pause")
        return lines

    def can_process(self, data: dict) -> bool:
        """判断参数是否可以处理"""
        return self.exists_param("Pause", data) or self.exists_param("TransScene", data)