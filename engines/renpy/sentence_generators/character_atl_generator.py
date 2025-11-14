from core.base_sentence_generator import BaseSentenceGenerator

class BackgroundATLGenerator(BaseSentenceGenerator):

    param_config = {
            "SpriteATLtype": {
            },
            "SpriteATL": {
            },
        }  

    @property
    def category(self):
        return "CharacterATL"

    @property
    def priority(self) -> int:
        return 251

    def process(self, data):
        if not self.can_process(data):
            return
        
        # data = self.do_translate(data)

        if self.exsits_param("SpriteATLtype", data):
            line = self.get_value("SpriteATL", data)

        return [line]