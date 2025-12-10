"""
Naninovel Audio Generator
生成音频相关命令（音乐、音效、语音）
"""
from core.base_sentence_generator import BaseSentenceGenerator


class AudioGenerator(BaseSentenceGenerator):
    """音频生成器"""

    # Music 资源配置
    resource_config_music = {
        "resource_type": "Music",
        "resource_category": "音频",
        "main_param": "Music",
        "part_params": [],
        "separator": "",
        "folder": "Audio/Music/"
    }

    # Sound 资源配置
    resource_config_sound = {
        "resource_type": "Sound",
        "resource_category": "音频",
        "main_param": "Sound",
        "part_params": [],
        "separator": "",
        "folder": "Audio/SFX/"
    }

    # Ambience 资源配置
    resource_config_ambience = {
        "resource_type": "Ambience",
        "resource_category": "音频",
        "main_param": "Ambience",
        "part_params": [],
        "separator": "",
        "folder": "Audio/SFX/"
    }

    param_config = {
            "Music": {
                "format_stop": "@stopBgm wait:false",
                "format": '@bgm Music/{value}',
                "translate_type": "Music",
            },
            "Sound": {
                "format_stop": "@stopSfx wait:false",
                "format": '@sfx SFX/{value}',
                "translate_type": "Sound",
            },
            "Ambience": {
                "format_stop": "@stopSfx wait:false",
                "format": '@sfx SFX/{value} loop:True',
                "translate_type": "Ambience",
            },
            "Volume": {
                "format": " volume:{value}",
            },

            "AudioFade": {
                "format": " fade:{value}",
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

        for param_name in ["Music", "Ambience", "Sound"]:
            line = ""
            param_value = self.get_value(param_name, data)
            if param_value == "stop":
                line = self.param_config[param_name].get("format_stop","")
            elif param_value:
                line = self.get_sentence(param_name, data)
                if self.exists_param("Volume", data) and line:
                    line += self.get_sentence("Volume", data)

            if self.exists_param("AudioFade", data) and line:
                line += self.get_sentence("AudioFade", data)
            
            if line:
                lines.append(line)

        return lines
