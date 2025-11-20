"""
Naninovel Character Generator
生成角色相关命令
"""
from core.base_sentence_generator import BaseSentenceGenerator
from engines.naninovel.param_processor import ParamProcessor


class CharacterGenerator(BaseSentenceGenerator):
    """角色生成器"""

    param_config = {
        "Char": {
            "translate_type": "Character"
        },
        "Varient": {
            "translate_type": "Varient"
        },
        "Pose": {},
        "Position": {
            "translate_type": "Position"
        },
        "Scale": {},
        "Visible": {},
        "Tint": ,
        "Wait": {},
        "Time": {}
    }

    def __init__(self, translator, engine_config):
        super().__init__(translator, engine_config)
        self.param_processor = ParamProcessor()

    @property
    def category(self):
        return "Character"

    @property
    def priority(self) -> int:
        return 200

    def process(self, data):
        """
        处理角色参数

        Args:
            data: 参数字典

        Returns:
            List[str]: 生成的角色命令
        """
        if not self.can_process(data):
            return None

        data = self.do_translate(data)

        char = data.get("Char")
        if not char:
            return []

        # 构建角色命令
        command = "@char "
        image = char

        # 添加变体
        if "Varient" in data:
            image += f".{data['Varient']}"

        # 添加各种参数
        pose = self.param_processor._process_pose_parameter(data.get("Pose"))
        position = self.param_processor._process_position_parameter(data.get("Position"))
        scale = self.param_processor._process_scale_parameter(data.get("Scale"))
        visible = self.param_processor._process_visible_parameter(data.get("Visible"))
        tint = self.param_processor._process_tint_parameter(data.get("Tint"))
        wait = self.param_processor._process_wait_parameter(data.get("Wait"))
        time = self.param_processor._process_time_parameter(data.get("Time"))

        # 构建最终命令
        result = f"{command}{image}{pose}{position}{scale}{visible}{tint}{wait}{time}"
        return [result]
