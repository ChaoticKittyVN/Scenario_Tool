from core.base_sentence_generator import BaseSentenceGenerator
from engines.renpy.param_processor import ParamProcessor as pm

class CharacterGenerator(BaseSentenceGenerator):

    param_config = {
            "CharacterCommand": {
                "translayte_type": "Command",
                "default": "show",
            },

            "Character": {
                "translate_type": "Character",
            },

            "Sprite": {
                "translate_type": "Sprite",
            },

            "Varient": {
                "translate_type": "Varient",
            },

            "Atr1": {
            },

            "Atr2": {
            },

            "Atr3": {
            },

            "SpriteAt": {
                "translate_type": "Transform",
                "format": " at {value}"
            },

            "SpriteOnlayer": {
                "translate_type": "Layer",
                "format": " onlayer {value}",
            },

            "SpriteWith": {
                "translate_type": "Transition",
                "format": " with {value}",
                "default": "dissolve"
            },

            "SpriteWithAtr": {
                "format": "({value})",
            },

            "SpriteATLtype": {
            },
        }
    
    @property
    def category(self):
        return "Character"


    
    @property
    def priority(self) -> int:
        return 250

    def process(self, data):
        if not self.can_process(data):
            return

        data = self.do_translate(data)

        lines = []

        """构建立绘命令"""
        # 检查是否有足够的上下文生成立绘命令
        
        if self.exsits_param("Character", data) or self.exsits_param("Sprite", data):

            line = ""
            character = self.get_value("Character", data)
            sprite = self. get_value("Sprite", data)

            image = character or sprite
            # 构建立绘命令
            command = self.get_value_default("CharacterCommand", data) + " "
            # 添加非层叠式图像属性 (ShowAtr0)
            varient = self.get_value("Varient", data)
            if varient:
                image = f"{image} {varient}"

            # 添加所有属性（差分）
            for i in range(1, 4):  # 支持最多3个属性
                atr_key = f"Atr{i}"
                if self.exsits_param(atr_key, data):
                    atr_value = self.get_value(atr_key, data)
                    image += f" {atr_value}"

            # 添加位置
            at = self.get_sentence("SpriteAt", data)

            # 添加图层
            onlayer = self.get_sentence("SpriteOnlayer", data)

            # 添加过渡效果
            transition = self.get_value_default("SpriteWith", data)
            if transition != "empty":
                transition = self.get_sentence_default("SpriteWith", data)
                with_atr = self.get_sentence("SpriteWithAtr", data)
                if with_atr:
                    transition += with_atr
            else:
                transition = ""

            # 构建最终命令
            line = f"{command}{image}{at}{onlayer}{transition}"

            if self.exsits_param("ATLtype", data):
                line = f"{line}:"

            lines.append(line)

        return lines