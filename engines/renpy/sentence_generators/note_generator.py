from core.base_sentence_generator import BaseSentenceGenerator

class NoteGenerator(BaseSentenceGenerator):
    
    @property
    def category(self):
        return "Note"

    @property
    def param_config(self) -> dict[str, dict]:
        return {
            "Note": {
                "format": "# {value}"
            },
        }    
    
    @property
    def priority(self) -> int:
        return 0

    def process(self, data):
        if not self.can_process(data):
            return

        note = self.get_sentence("Note", data)

        return [note]