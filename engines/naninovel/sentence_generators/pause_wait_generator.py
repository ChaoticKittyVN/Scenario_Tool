from core.base_sentence_generator import BaseSentenceGenerator

class PauseWaitGenerator(BaseSentenceGenerator):
    """等待时间生成器"""


    param_config = {
        "PauseWait": {
            "format": "@wait {value}"
        }
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

        wait = self.get_sentence("WaitPause", data)

        return [wait]