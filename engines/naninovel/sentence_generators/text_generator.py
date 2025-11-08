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
        printer = data.get("Printer")
        hide_printer = data.get("HidePrinter")

        results = []

        if printer:
            printer = self.translator.translate("Printer",printer)
            printer_pos = data.get("PrinterPos")

            temp = f"@printer {printer}"
            if printer_pos:
                temp += f" pos:{printer_pos}"
            results.append(temp)

        if speaker:
            if speaker == "naninovel":
                results.append(text)
                pass
            else:
                speaker = self.translator.translate("Speaker",speaker)
                results.append(f'{speaker}: {text}')
                pass
        else:
            if text:
                results.append(text)

        if hide_printer:
            results.append("@hidePrinter")

        return results