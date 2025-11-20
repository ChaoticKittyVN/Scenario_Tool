"""
Ren'Py Pause Generator
生成暂停命令
"""
from core.base_sentence_generator import BaseSentenceGenerator


class PauseGenerator(BaseSentenceGenerator):
    """暂停生成器"""

    param_config = {
        "Pause": {}
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

        pause = self.get_value("Pause", data)
        if not pause:
            return []

        if pause == "hard":
            return ["pause"]
        else:
            try:
                pause_time = float(pause)
                return [f"pause {pause_time}"]
            except ValueError:
                return ["pause"]
