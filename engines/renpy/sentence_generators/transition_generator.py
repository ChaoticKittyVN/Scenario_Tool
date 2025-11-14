from core.base_sentence_generator import BaseSentenceGenerator

class TransitionGenerator(BaseSentenceGenerator):

    param_config = {
            "UseTrans":{
            },
            "TransWith": {
                "translate_type": "Transition",
                "format": " with {value}",
                "default": "Dissolve"
            },
            "TransWithAtr": {
                "format": "({value})",
                "default": "1.0"
            },
        }
    
    @property
    def category(self):
        return "Transition"
    
    @property
    def priority(self) -> int:
        return 800

    def process(self, data):
        if not self.can_process(data):
            return

        data = self.do_translate(data)

        lines = []
        
        # 处理全局转场效果
        trans_with = self.get_value_default("TransWith", data)

        # 处理转场效果属性
        if trans_with.istitle():
            trans_with_atr = self.get_sentence_default("TransWithAtr", data)
            trans_with = f"{trans_with}{trans_with_atr}"
        
        # 构建转场命令
        line = f"with {trans_with}"
        lines.append(line)
        
        return lines