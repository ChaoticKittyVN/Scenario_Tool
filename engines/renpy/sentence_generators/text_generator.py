from core.base_sentence_generator import BaseSentenceGenerator

class TextGenerator(BaseSentenceGenerator):

    @property
    def category(self):
        return "Text"

    @property
    def priority(self) -> int:
        return 900

    def process(self, data):
        if not self.can_process(data):
            return

        speaker = data.get("Speaker")
        text = data.get("Text")
        wd_show = data.get("WindowShow")
        wd_hide = data.get("WindowHide")

        results = []

        if wd_show:
            results.append("window show")

        if speaker:
            if speaker == "renpy":
                results.append(text)
            else:
                speaker = self.translator.translate("Speaker",speaker)
                results.append(f'{speaker} "{text}"')
        else:
            if text:
                results.append(f'"{text}"')

        if wd_hide:
            results.append("window hide")

        return results