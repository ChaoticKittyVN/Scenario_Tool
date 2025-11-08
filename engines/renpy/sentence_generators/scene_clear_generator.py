from core.base_sentence_generator import BaseSentenceGenerator

class SceneClearGenerator(BaseSentenceGenerator):

    @property
    def category(self):
        return "SceneClear"

    @property
    def priority(self) -> int:
        return 150

    def process(self, data):
        if not self.can_process(data):
            return
        
        data = self.do_translate(data)

        value = data.get("SceneOnlayer")

        return [f"scene onlayer {value}"]