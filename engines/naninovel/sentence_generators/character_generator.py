from core.base_sentence_generator import BaseSentenceGenerator
from engines.naninovel.param_processor import ParamProcessor as pm

param_processor = pm()

class CharacterGenerator(BaseSentenceGenerator):
    
    @property
    def default_param(self) -> dict[str, str]:
        return {
            "Char": "",
            "Varient": "",
            "Pose": "",
            "Position": "",
            "Scale": "1",
            "Visible": "true",
            "Tint": "",
            "Wait": "true",
            "Time": "1"
        }
    
    @property
    def category(self):
        return "Character"

    @property
    def priority(self) -> int:
        return 200

    def process(self, data):
        if not self.can_process(data):
            return

        data = self.do_translate(data)

        """构建角色命令"""
        # 检查是否有足够的上下文生成角色命令
        char = data.get("Char")
        
        if not char:
            return []
        
        # 构建角色命令
        command = "@char "
        image = char
        
        # 添加变体
        if "Varient" in data:
            image += f".{data['Varient']}"
        
        # 添加姿势
        pose = param_processor._process_pose_parameter(data.get("Pose"))
        
        # 添加位置
        position = param_processor._process_position_parameter(data.get("Position"))
        
        # 添加缩放
        scale = param_processor._process_scale_parameter(data.get("Scale"))
        
        # 添加可见性
        visible = param_processor._process_visible_parameter(data.get("Visible"))
        
        # 添加色调
        tint = param_processor._process_tint_parameter(data.get("Tint"))
        
        # 添加等待参数
        wait = param_processor._process_wait_parameter(data.get("Wait"))
        
        # 添加时间参数
        time = param_processor._process_time_parameter(data.get("Time"))
        
        # 构建最终命令
        result = f"{command}{image}{pose}{position}{scale}{visible}{tint}{wait}{time}"
        return [result]