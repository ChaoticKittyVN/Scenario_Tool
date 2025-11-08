from core.base_sentence_generator import BaseSentenceGenerator

class AudioGenerator(BaseSentenceGenerator):
    
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
                temp = f"stop {name.lower()}"
            else:
                temp = f"play {name.lower()} {value}"
            results.append(temp)

        return results