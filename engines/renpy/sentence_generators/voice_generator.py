"""
Ren'Py Voice Generator
生成语音命令
"""
from core.base_sentence_generator import BaseSentenceGenerator


class VoiceGenerator(BaseSentenceGenerator):
    """语音生成器"""

    # Voice 资源配置
    resource_config = {
        "resource_type": "Voice",
        "resource_category": "音频",
        "main_param": "Voice",
        "part_params": [],
        "separator": "",
        "folder": "audio/Voice/"
    }

    param_config = {
        "Voice": {
            "translate_type": "Voice"
        }
    }

    @property
    def category(self):
        return "Voice"

    @property
    def priority(self) -> int:
        return 890

    def process(self, data):
        """
        处理语音参数

        Args:
            data: 参数字典

        Returns:
            List[str]: 生成的语音命令
        """
        if not self.can_process(data):
            return None

        data = self.do_translate(data)

        voice = self.get_value("Voice", data)
        if not voice:
            return []

        if voice == "stop":
            return ["stop voice"]
        else:
            return [f"voice {voice}"]
