"""
Utage Fade Generator
生成转场命令
"""
from typing import Any, Dict, Optional
from core.dict_based_sentence_generator import DictBasedSentenceGenerator


class FadeGenerator(DictBasedSentenceGenerator):
    """渐变转场生成器"""

    param_config = {
        "FadeType": {
            "key": "Command",
            "translate_type": "FadeType"
        },
        "FadeColor": {
            "key": "Arg1",
            "translate_type": "FadeColor"
        },
        "FadeCamera": {
            "key": "Arg2",
        },
        "FadeRule": {
            "translate_type": "Rule",
            "key": "Arg3",
        },
        "FadeTime": {
            "key": "Arg6",
            "default": "1.0"
        },
    }

    @property
    def category(self):
        return "Fade"

    @property
    def priority(self) -> int:
        return 150

    def process(self, data: Dict[str, Any]) -> Optional[list]:
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

        line = {}
        self._set_param_fast(line, "FadeType", data)
        self._set_param_fast(line, "FadeColor", data)
        self._set_param_fast(line, "FadeCamera", data)
        self._set_param_fast(line, "FadeRule", data)
        self._set_param_fast(line, "FadeTime", data)

        return [line]
