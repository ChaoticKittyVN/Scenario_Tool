from core.base_sentence_generator import BaseSentenceGenerator

class VoiceGenerator(BaseSentenceGenerator):
    
    @property
    def category(self):
        return "Movie"

    # TODO 注释文档
    @property
    def priority(self) -> int:
        return 10

    def process(self, data):
        if not self.can_process(data):
            return
        
        results = []

        movie = data.get("Moive")

        temp = f"@movie {movie}"
        results.append(temp)

        return results