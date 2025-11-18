from core.base_sentence_generator import BaseSentenceGenerator

class VoiceGenerator(BaseSentenceGenerator):

    param_config = {
            "Voice": {
                "translate_type": "Layer",
                "format": "voice {value}"
            },
        }
    
    @property
    def category(self):
        return "Voice"
    
    @property
    def priority(self) -> int:
        return 899

    def process(self, data):
        if not self.can_process(data):
            return

        line = self.get_sentence("Voice", data)

        if line == "stop":
            line = "voice stop"

        return [line]