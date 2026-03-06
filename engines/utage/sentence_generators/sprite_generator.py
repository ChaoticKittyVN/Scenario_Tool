"""
Utage Sprite Generator
生成精灵图相关命令
"""
from typing import Any, Dict, Optional
from core.dict_based_sentence_generator import DictBasedSentenceGenerator


class SpriteGenerator(DictBasedSentenceGenerator):
    """精灵图生成器"""

    # 精灵图资源配置
    resource_config = {
        "resource_type": "Sprite",
        "resource_category": "图片",
        "main_param": "Sprite",
        "part_params": [],
        "separator": " ",
        "folder": "Texture/Sprite/"
    }

    param_config = {
        "Sprite": {
            "validate_type": "Sprite",
            "key": "Arg1"
        },
        "SpriteAtr": {},
        "SpriteLayer": {
            "validate_type": "SpriteLayer",
            "key": "Arg3"
        }
    }

    @property
    def category(self):
        return "Sprite"

    @property
    def priority(self) -> int:
        return 600

    def can_process(self, data: Dict[str, Any]) -> bool:
        return super().can_process(data) and (
            "Sprite" in data
        )

    def process(self, data: Dict[str, Any]) -> Optional[list]:
        """
        构建精灵图命令

        Args:
            data: 参数字典

        Returns:
            List[Dict[str, Any]]: 生成的精灵图命令
        """
        # 快速检查是否可以处理
        if not self.can_process(data):
            return None

        line = self.create_command_dict("Sprite")
        sprite = self.get_value("Sprite", data)
        if self.exists_param("SpriteAtr", data):
            sprite += self.get_value("SpriteAtr", data)
        line["Arg1"] = sprite
        self._set_param_fast(line, "SpriteLayer", data)

        return [line]
