from core.base_sentence_generator import BaseSentenceGenerator
from engines.renpy.param_processor import ParamProcessor as pm

param_processor = pm()

class HiedeGenerator(BaseSentenceGenerator):
    
    @property
    def category(self):
        return "Hide"

    @property
    def priority(self) -> int:
        return 400

    def process(self, data):
        if not self.can_process(data):
            return

        data = self.do_translate(data)


        """构建隐藏和转场命令"""
        results = []

        # 处理隐藏命令
        hide = data.get("Hide")
        if hide:
            command = "hide "
            image = hide
            
            # 添加图层
            onlayer = param_processor._process_onlayer_parameter(data.get("HideOnlayer"))
            
            # 添加过渡效果
            transition = param_processor._process_transition_parameter(data.get("HideWith"), data.get("HideWithAtr"), "dissolve")
            
            # 构建隐藏命令
            result = f"{command}{image}{onlayer}{transition}"
            results.append(result)

        return results