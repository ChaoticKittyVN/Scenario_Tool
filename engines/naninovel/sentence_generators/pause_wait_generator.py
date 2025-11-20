from core.base_sentence_generator import BaseSentenceGenerator

class PuaseWaitGenerator(BaseSentenceGenerator):

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

        wait = data.get("WaitPause")
        if wait:
            return [f"@wait {wait}"]
        return []