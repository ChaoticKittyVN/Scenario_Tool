"""
Ren'Py Scene Clear Generator
生成场景清除命令
"""
from core.base_sentence_generator import BaseSentenceGenerator


class SceneClearGenerator(BaseSentenceGenerator):
    """场景清除生成器"""

    param_config = {
        "SceneClear": {
            "translate_type": "Layer"
        }
    }

    @property
    def category(self):
        return "SceneClear"

    @property
    def priority(self) -> int:
        return 50

    def process(self, data):
        """
        处理场景清除参数

        Args:
            data: 参数字典

        Returns:
            List[str]: 生成的场景清除命令
        """
        if not self.can_process(data):
            return None

        data = self.do_translate(data)

        layer = self.get_value("SceneClear", data)
        if not layer:
            return []

        return [f"scene onlayer {layer}"]
