from core.base_sentence_generator import BaseSentenceGenerator
from engines.renpy.param_processor import ParamProcessor as pm

param_processor = pm()

class BackgroundGenerator(BaseSentenceGenerator):
    
    @property
    def category(self):
        return "Background"

    @property
    def priority(self) -> int:
        return 200

    def process(self, data):
        """构建场景命令"""
        # 检查是否有足够的上下文生成场景命令
        if not self.can_process(data):
            return

        data = self.do_translate(data)

        background = data.get("Background")
        event = data.get("Event")
        
        if not background and not event:
            return []
        
        # 构建场景命令
        command = "scene " if data.get("UseScene") else "show "
        image = background or event
        
        # 添加事件属性（差分）
        if event and data.get("EventAtr"):
            image += f" {data['EventAtr']}"
        
        # 添加位置
        at = param_processor._process_at_parameter(data.get("At"))
        
        # 添加图层
        onlayer = param_processor._process_onlayer_parameter(data.get("Onlayer"))
        
        # 添加过渡效果
        transition = param_processor._process_transition_parameter(data.get("With"), data.get("WithAtr"), "dissolve")
        
        # 构建最终命令
        result = f"{command}{image}{at}{onlayer}{transition}"
        return [result]
