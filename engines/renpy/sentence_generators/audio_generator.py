from core.base_sentence_generator import BaseSentenceGenerator

class AudioGenerator(BaseSentenceGenerator):

    param_config ={
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
                "fadeout_format": " fadeout {value}",
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
        if not self.can_process(data):
            return


        data = self.do_translate(data)

        results = []
        
        music = self.get_value("Music", data)
        ambience = self.get_value("Ambience", data)
        sound = self.get_value("Sound", data)
        volume = self.get_value("Volume", data)
        audio_fade = self.get_value("AudioFade", data)

        for param_name,param_value in {"Music": music, "Ambience": ambience, "Sound": sound}.items():
            if param_value:
                config = self.param_config[param_name]
                if param_value == config["match_word"]:
                    # 停止命令
                    line = config["stop_format"]
                    if audio_fade:
                        fade_config = self.param_config["AudioFade"]
                        fade = fade_config["fadeout_format"].format(value=audio_fade)
                        line = f"{line}{fade}"
                else:
                    # 播放命令
                    line = self.get_sentence(param_name, data)
                    
                    # 如果有Volume，合并到播放命令中
                    if volume:
                        volume_cmd = self.get_sentence("Volume", data)
                        line = f"{line}{volume_cmd}"
                    
                    if audio_fade:
                        fade = self.get_sentence("AudioFade", data)
                        line = f"{line}{fade}"

                results.append(line)

        return results