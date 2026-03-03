"""
Utage Wait Generator
生成等待命令
"""
from typing import Any, Dict, Optional
from core.dict_based_sentence_generator import DictBasedSentenceGenerator


class WaitGenerator(DictBasedSentenceGenerator):
    """等待生成器"""

    param_config = {
        "Wait": {
            "key": "Arg6"
        }
    }

    @property
    def category(self):
        return "Wait"

    @property
    def priority(self) -> int:
        return 500

    def process(self, data: Dict[str, Any]) -> Optional[list]:
        """
        处理等待参数

        Args:
            data: 参数字典

        Returns:
            Dict[str, Any]: 生成的等待命令
        """
        if not self.can_process(data):
            return None

        line = {}
        self.set_command(line, "Wait")
        self._set_param_fast(line, "Wait", data)

        return [line]


