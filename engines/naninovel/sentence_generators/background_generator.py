from core.base_sentence_generator import BaseSentenceGenerator
from engines.naninovel.param_processor import ParamProcessor as pm

param_processor = pm()

class BackgroundGenerator(BaseSentenceGenerator):
    
    @property
    def default_param(self) -> dict[str, str]:
        return {
            "Back": "",
            "BackID": "",
            "BackScale": "",
            "BackPos": "",
            "BackVisible": "",
            "BackWait": "",
            "Dissolve": "",
            "DissolveParam": "",
            "BackTime": ""
        }
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

        """构建场景命令"""
        # 检查是否有足够的上下文生成场景命令
        background = data.get("Back")
        
        if not background:
            return []
        
        # 构建场景命令
        image = background
        
        # 添加图层
        id = param_processor._process_id_parameter(data.get("BackID"))
        
        # 添加位置和缩放变换
        pos = param_processor._process_pos_parameter(data.get("BackPos"))
        
        scale = param_processor._process_scale_parameter(data.get("BackScale"))

        # 是否可见
        visible = param_processor._process_visible_parameter(data.get("BackVisible"))

        # 添加渐变遮罩
        dissolve = param_processor._process_dissolve_parameter(data.get("Dissolve"),data.get("DissolveParam"))

        # 是否等待
        wait = param_processor._process_wait_parameter(data.get("BackWait"))

        # 等待时间
        time = param_processor._process_time_parameter(data.get("BackTime"))

        # 构建最终命令
        result = f"@back {image}{id}{pos}{scale}{visible}{dissolve}{wait}{time}"
        return [result]
