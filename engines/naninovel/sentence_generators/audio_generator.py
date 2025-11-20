"""
Naninovel Audio Generator
生成音频相关命令（音乐、音效、语音）
"""
from core.base_sentence_generator import BaseSentenceGenerator


class AudioGenerator(BaseSentenceGenerator):
    """音频生成器"""

    param_config = {
        "Music": {
            "translate_type": "Music",
        },
        "Sound": {
            "translate_type": "Sound",
        },
        "Voice": {
            "translate_type": "Voice",
        },
    }

    @property
    def category(self):
        return "Audio"

    @property
    def priority(self) -> int:
        return 100

    def process(self, data):
        """
        处理音频参数

        Args:
            data: 参数字典

        Returns:
            List[str]: 生成的音频命令
        """
        if not self.can_process(data):
            return None

        data = self.do_translate(data)
        results = []

        # 处理音乐
        if "Music" in data:
            music = data["Music"]
            if music == "stop":
                results.append("@stopBgm")
            else:
                results.append(f"@bgm Music/{music}")

        # 处理音效
        if "Sound" in data:
            sound = data["Sound"]
            if sound == "stop":
                results.append("@stopSfx")
            else:
                results.append(f"@sfx SFX/{sound}")

        # 处理语音
        if "Voice" in data:
            voice = data["Voice"]
            if voice == "stop":
                results.append("@stopVoice")
            else:
                results.append(f"@voice {voice}")

        return results
