from core.base_sentence_generator import BaseSentenceGenerator

class TextGenerator(BaseSentenceGenerator):

    param_config = {
            "Window": {
                "translate_type": "Window"
            },

            "Speaker": {
                "translate_type": "Speaker",
            },

            "Text": {
            },
        }
    
    @property
    def category(self):
        return "Text"
    
    @property
    def priority(self) -> int:
        return 900

    def process(self, data):
        if not self.can_process(data):
            return

        speaker = self.get_value("Speaker", data)
        text = self.get_value("Text", data)
        window = self.get_value("Window", data)

        lines = []
        
        if window in ["显示", "显示和隐藏"]:
            lines.append("window show")

        if speaker:
            if speaker == "renpy":
                lines.append(text)
            else:
                speaker = self.translator.translate("Speaker",speaker)
                lines.append(f'{speaker} "{text}"')
        else:
            if text:
                lines.append(f'"{text}"')

        if window in ["隐藏", "显示和隐藏"]:
            lines.append("window hide")

        return lines