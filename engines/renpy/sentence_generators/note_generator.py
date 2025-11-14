from core.base_sentence_generator import BaseSentenceGenerator

class NoteGenerator(BaseSentenceGenerator):

    param_config ={
            "Note": {
                "format": "# {value}"
            },
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

        note = self.get_sentence("Note", data)

        return [note]