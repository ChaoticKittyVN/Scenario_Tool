"""
Naninovel Hide Generator
生成隐藏命令
"""
from core.base_sentence_generator import BaseSentenceGenerator
from engines.naninovel.param_processor import ParamProcessor


class HideGenerator(BaseSentenceGenerator):
    """隐藏生成器"""

    param_config = {
        "Hide": {
            "translate_type": "Character"
        },
        "HideWait": {}
    }

    def __init__(self, translator, engine_config):
        super().__init__(translator, engine_config)
        self.param_processor = ParamProcessor()

    @property
    def category(self):
        return "Hide"

    @property
    def priority(self) -> int:
        return 300

    def process(self, data):
        """
        处理隐藏参数

        Args:
            data: 参数字典

        Returns:
            List[str]: 生成的隐藏命令
        """
        if not self.can_process(data):
            return None

        data = self.do_translate(data)

        hide_target = data.get("Hide")
        if not hide_target:
            return []

        wait = self.param_processor._process_wait_parameter(data.get("HideWait"))
        result = f"@hide {hide_target}{wait}"
        return [result]
