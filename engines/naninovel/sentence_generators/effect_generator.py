from core.base_sentence_generator import BaseSentenceGenerator


class EffectGenerator(BaseSentenceGenerator):
    
    @property
    def category(self):
        return "Effect"

    # TODO 未编写新逻辑
    @property
    def priority(self) -> int:
        return 120

    def process(self, data):
        if not self.can_process(data):
            return
        
        data = self.do_translate(data)

        lines = []




        return lines