"""
Ren'Py Character Generator
生成角色立绘相关命令
"""
from core.base_sentence_generator import BaseSentenceGenerator


class CharacterGenerator(BaseSentenceGenerator):
    """角色生成器"""

    # 资源配置 - 用于资源验证
    resource_config = {
        "resource_type": "Character",
        "resource_category": "图片",
        "main_param": "Character",
        "part_params": ["Varient", "Atr1", "Atr2", "Atr3"],
        "separator": " ",
        "folder": "images/Character/"
    }

    # Sprite 资源配置
    resource_config_sprite = {
        "resource_type": "Sprite",
        "resource_category": "图片",
        "main_param": "Sprite",
        "part_params": ["Varient", "Atr1", "Atr2", "Atr3"],
        "separator": " ",
        "folder": "images/Sprite/"
    }

    param_config = {
        "SpriteCommand": {
            "translate_type": "Command",
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
        "Atr1": {},
        "Atr2": {},
        "Atr3": {},
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
        "SpriteATLType": {},
    }

    @property
    def category(self):
        return "Character"

    @property
    def priority(self) -> int:
        return 250

    def process(self, data):
        """
        构建立绘命令

        Args:
            data: 参数字典

        Returns:
            List[str]: 生成的角色命令
        """
        if not self.can_process(data):
            return None

        data = self.do_translate(data)
        lines = []

        if self.exists_param("Character", data) or self.exists_param("Sprite", data):
            character = self.get_value("Character", data)
            sprite = self.get_value("Sprite", data)

            image = character or sprite
            # 构建立绘命令
            command = self.get_value("SpriteCommand", data, use_default=True) + " "

            # 添加非层叠式图像属性
            varient = self.get_value("Varient", data)
            if varient:
                image = f"{image} {varient}"

            # 添加所有属性（差分）
            for i in range(1, 4):  # 支持最多3个属性
                atr_key = f"Atr{i}"
                if self.exists_param(atr_key, data):
                    atr_value = self.get_value(atr_key, data)
                    image += f" {atr_value}"

            # 添加位置
            at = self.get_sentence("SpriteAt", data)

            # 添加图层
            onlayer = self.get_sentence("SpriteOnlayer", data)

            # 添加过渡效果
            transition = self.get_value("SpriteWith", data, use_default=True)
            if transition != "empty":
                transition = self.get_sentence("SpriteWith", data, use_default=True)
                with_atr = self.get_sentence("SpriteWithAtr", data)
                if with_atr:
                    transition += with_atr
            else:
                transition = ""

            # 构建最终命令
            line = f"{command}{image}{at}{onlayer}{transition}"

            if self.exists_param("SpriteATLType", data):
                line = f"{line}:"

            lines.append(line)

        return lines
