from core.base_sentence_generator import BaseSentenceGenerator

class SceneClearGenerator(BaseSentenceGenerator):

    param_config = {
            "Pause": {
                "format": "pause {value}"
            },
        }
    
    @property
    def category(self):
        return "Pause"
    
    @property
    def priority(self) -> int:
        return 850

    def process(self, data):
        if not self.can_process(data):
            return

        line = self.get_sentence("Pause", data)

        return [line]