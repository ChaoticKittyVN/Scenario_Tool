from core.base_sentence_generator import BaseSentenceGenerator

class AudioGenerator(BaseSentenceGenerator):
    
    param_config ={
            "Music": {
                "translate_type": "Music",
                "match_word": "stop",
                "stop_format": "@stopBgm wait:False",
                "format": '@bgm Music/{value}',
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

        for name,value in data.items():
            if value == "stop":
                temp = self.format_config.get(name).get("format_stop")
            else:
                temp = self.format_config.get(name).get("format").format(value=value)
            results.append(temp)

        return results