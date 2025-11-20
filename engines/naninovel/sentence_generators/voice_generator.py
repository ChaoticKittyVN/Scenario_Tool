from core.base_sentence_generator import BaseSentenceGenerator

class VoiceGenerator(BaseSentenceGenerator):
    param_config = {
        "Voice": {
            "format_stop": "@stopVoice",
            "format": '@voice {value}',
        },
    }


    @property
    def category(self):
        return "Voice"

    @property
    def priority(self) -> int:
        return 890

    def process(self, data):
        if not self.can_process(data):
            return
        

        voice = self.get_value("Voice", data)

        if voice == "stop":
            line = self.param_config.get("Voice", {}).get("format_stop", "")
        else:
            line = self.get_sentence("Voice", data)
            
        return [line]