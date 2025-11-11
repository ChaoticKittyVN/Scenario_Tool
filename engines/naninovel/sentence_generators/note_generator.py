from core.base_sentence_generator import BaseSentenceGenerator

class NoteGenerator(BaseSentenceGenerator):
    
    @property
    def default_param(self) -> dict[str, str]:
        return {
            "Note": ""
        }
    
    @property
    def category(self):
        return "Note"

    @property
    def priority(self) -> int:
        return 0

    def process(self, data):
        if not self.can_process(data):
            return

        temp = data.get("Note",None)
        if temp:
            value = f"; {temp}"
        else:
            return []
        return [value]