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
                "match_word": "stop",
                "stop_format": "stop music",
                "format": "play music {value}",
            },

            "Ambience": {
                "translate_type": "Ambience",
                "match_word": "stop",
                "stop_format": "stop ambience",
                "format": "play ambience {value}",
            },

            "Sound": {
                "translate_type": "Sound",
                "match_word": "stop",
                "stop_format": "stop sound",
                "format": "play sound {value}",
            },
            "Volume": {
                "format": " volume {value}",
            },

            "AudioFade": {
                "format": " fadein {value}",
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
        lines = []


        for audio in ["Music", "Sound", "Ambience"]:
            if audio in data:
                audio_value = data[audio]
                line = []
                if audio_value == "stop":
                    line = self.param_config[audio]["stop_format"]
                    if self.exists_param("AudioFade", data):
                        line += f" fadeout {self.get_value('AudioFade', data)}"
                else:
                    line = self.get_sentence(audio, data)
                    if self.exists_param("Volume", data):
                        line += self.get_sentence("Volume", data)
                    if self.exists_param("AudioFade", data):
                        line += self.get_sentence("AudioFade", data)
                lines.append(line)

        return lines
