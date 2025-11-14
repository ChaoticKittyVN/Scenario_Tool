from core.base_sentence_generator import BaseSentenceGenerator

class SceneClearGenerator(BaseSentenceGenerator):

    param_config = {
            "ClearLayer": {
                "translate_type": "Layer",
                "format": "scene onlayer {value}"
            },
        }
    
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

        if self.exsits_param("ClearLayer", data):
            line = self.get_sentence("ClearLayer", data)

        return [line]