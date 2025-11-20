"""
Ren'Py Note Generator
生成注释命令
"""
from core.base_sentence_generator import BaseSentenceGenerator


class NoteGenerator(BaseSentenceGenerator):
    """注释生成器"""

    param_config = {
        "Note": {}
    }

    @property
    def category(self):
        return "Note"

    @property
    def priority(self) -> int:
        return 0

    def process(self, data):
        """
        处理注释参数

        Args:
            data: 参数字典

        Returns:
            List[str]: 生成的注释命令
        """
        if not self.can_process(data):
            return None

        note = data.get("Note")
        if note:
            return [f"# {note}"]
        return []
