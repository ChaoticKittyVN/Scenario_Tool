from core.base_sentence_generator import BaseSentenceGenerator

class AudioGenerator(BaseSentenceGenerator):
    
    @property
    def param_config(self) -> dict[str, dict]:
        return {
            "Music": "",
            "Ambience": "",
            "Sound": "",
            "Volume": "",
            "AudioFade": "",
            "Voice": ""
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