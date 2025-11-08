from core.base_sentence_generator import BaseSentenceGenerator
from engines.renpy.param_processor import ParamProcessor as pm

param_processor = pm()

class FigureGenerator(BaseSentenceGenerator):
    
    @property
    def category(self):
        return "Figure"

    @property
    def priority(self) -> int:
        return 200

    def process(self, data):
        if not self.can_process(data):
            return

        data = self.do_translate(data)

        """构建立绘命令"""
        # 检查是否有足够的上下文生成立绘命令
        show = data.get("Show")
        
        if not show:
            return []
        
        # 构建立绘命令
        command = "show "
        image = show
        
        # 添加非层叠式图像属性 (ShowAtr0)
        if "ShowAtr0" in data:
            image += f" {data['ShowAtr0']}"

        # 添加所有属性（差分）
        for i in range(1, 4):  # 支持最多3个属性
            atr_key = f"ShowAtr{i}"
            if atr_key in data:
                image += f" {data[atr_key]}"
        
        # 添加位置
        at = param_processor._process_at_parameter(data.get("ShowAt"))
        
        # 添加图层
        onlayer = param_processor._process_onlayer_parameter(data.get("ShowOnlayer"))
        
        # 添加过渡效果
        transition = param_processor._process_transition_parameter(data.get("ShowWith"), data.get("ShowWithAtr"), "dissolve")
        
        # 添加ATL
        atl = param_processor._process_atl_parameter(data.get("ShowATL"))
        
        # 构建最终命令
        result = f"{command}{image}{at}{onlayer}{transition}{atl}"
        return [result]