"""
Ren'Py Audio Generator
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
        "Ambience": {
            "translate_type": "Ambience",
        },
        "Volume": {},
        "AudioFade": {},
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
                results.append("stop music")
            else:
                cmd = f"play music {music}"
                if "Volume" in data:
                    cmd += f" volume {data['Volume']}"
                if "AudioFade" in data:
                    cmd += f" fadein {data['AudioFade']}"
                results.append(cmd)

        # 处理音效
        if "Sound" in data:
            sound = data["Sound"]
            if sound == "stop":
                results.append("stop sound")
            else:
                results.append(f"play sound {sound}")

        # 处理环境音
        if "Ambience" in data:
            ambience = data["Ambience"]
            if ambience == "stop":
                results.append("stop ambience")
            else:
                results.append(f"play ambience {ambience}")

        return results
