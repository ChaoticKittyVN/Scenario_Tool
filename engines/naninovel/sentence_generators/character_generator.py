"""
Naninovel Character Generator
生成角色相关命令
"""
from core.base_sentence_generator import BaseSentenceGenerator


class CharacterGenerator(BaseSentenceGenerator):
    """角色生成器"""

    # 资源配置 - 用于资源验证
    resource_config = {
        "resource_type": "Char",
        "resource_category": "图片",
        "main_param": "Char",
        "part_params": ["Varient"],
        "separator": ".",
        "folder": "Characters/"
    }

    param_config = {
        "TransChar": {
            "category": "Character"
        },

        "Char": {
            "translate_type": "Character",
        },

        "Varient": {
            "translate_type": "Varient"
        },

        "Pose": {
            "translate_type": "Pose",
            "format": " pose:{value}"
        },

        "Position": {
            "format": " position:{value}"
        },

        "Scale": {
            "format": " scale:{value}"
        },

        "Visible": {
            "format": " visible:{value}"
        },

        "Tint": {
            "translate_type": "Tint",
            "format": " tint:{value}"
        },

        "Wait": {
            "format": " wait:true"
        },

        "Time": {
            "format": " time:{value}",
            "default": "0.5"
        },

        "CharAnim": {
            "translate_type": "Character",
        },

        "CharAnimParam": {
            "translate_type": "Animation"
        },

        "CharAnimWait": {},
    }

    def __init__(self, translator, engine_config):
        super().__init__(translator, engine_config)

    @property
    def category(self):
        return "Character"

    @property
    def priority(self) -> int:
        return 300

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

        """构建角色命令"""
        # 检查是否有足够的上下文生成角色命令
        char = self.get_value("Char", data)
        anim = self.get_value("CharAnimParam", data)

        if not char and not anim:
            return []
        
        lines = []
        trans = self.get_value("TransChar", data)

        if trans == "block":
            command = "    "
        else:
            command = ""

        if char == "hideAll":
            lines.append("@hideChars")
            # 构建角色命令

        else:
            image = char
            varient = self.get_value("Varient", data)

            # 使用varient_data时使用以下指令进行翻译
            # self.translator._translate_varient(varient,image)

            # 差分名，如有需要使用多参数组合
            image += f".{varient}"

            if trans == "hide":
                command += "@hide "
            else:
                command += "@char "

            # 添加姿势
            pose = self.get_sentence("Pose", data)
            
            # 添加位置
            position = pose = self.get_sentence("Position", data)
            
            # 添加缩放
            scale = self.get_sentence("Scale", data)
            
            # 添加可见性
            visible = self.get_sentence("Visible", data)
            
            # 添加色调
            tint = self.get_sentence("Tint", data)
            
            # 添加等待参数
            wait = self.get_sentence("Wait", data)

            line = (f"{command}{image}{pose}{position}{scale}{visible}{tint}{wait}")
            # 构建最终命令
            if trans == "trans":
                time = self.get_sentence("Time", data, use_default=True)
                lines.append(f"@trans{time}")
                lines.append("    @hideChars")
                lines.append(line)
            else:
                time = self.get_sentence("Time", data)
                lines.append(f"{line}{time}")

        if anim:
            char_anim = self.get_value("CharAnim", data)
            if not char_anim:
                char_anim = char
            
            anim = self.get_value("CharAnimParam", data)

            anim_wait = ""

            if self.exists_param("CharAnimWait", data):
                anim_wait = " wait:true"

            lines.append(f"@animate {char} {anim}{anim_wait}")

        return lines
