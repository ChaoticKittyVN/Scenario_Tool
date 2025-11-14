from core.base_sentence_generator import BaseSentenceGenerator

class BackgroundATLGenerator(BaseSentenceGenerator):

    param_config = {
            "ATLtype": {
            },
            "ATL": {
            },
        } 
    
    @property
    def category(self):
        return "BackgroundATL"

   
    
    @property
    def priority(self) -> int:
        return 201

    def process(self, data):
        if not self.can_process(data):
            return
        
        # data = self.do_translate(data)

        if self.exsits_param("ATLtype", data):
            line = self.get_value("ATL", data)

        return [line]