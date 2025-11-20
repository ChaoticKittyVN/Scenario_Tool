"""
Ren'Py Character ATL Generator
生成角色 ATL 动画命令（继承自 ATLGenerator）
"""
from engines.renpy.sentence_generators.atl_generator import ATLGenerator


class SpriteATLGenerator(ATLGenerator):
    """角色 ATL 动画生成器"""

    param_config = {
        "SpriteATLType": {
            "translate_type": "ATLtype",
        },
        "SpriteATLWarp": {
            "translate_type": "Warp",
            "default": "linear"
        },
        "SpriteATLTime": {
            "default": "1.0"
        },
        "SpriteATLTransform": {
            "translate_type": "Transform"
        },
        "SpriteATLValue": {},
    }

    @property
    def category(self):
        return "SpriteATL"

    @property
    def priority(self) -> int:
        return 251

    def process(self, data):
        """
        处理角色 ATL 参数（使用父类逻辑，只是参数名不同）

        Args:
            data: 参数字典

        Returns:
            List[str]: 生成的 ATL 命令
        """
        if not self.can_process(data):
            return None

        # 将 Sprite 前缀的参数映射到标准 ATL 参数名
        mapped_data = {}
        for key, value in data.items():
            if key.startswith("Sprite"):
                # 移除 Sprite 前缀
                new_key = key.replace("Sprite", "", 1)
                mapped_data[new_key] = value
            else:
                mapped_data[key] = value

        # 调用父类的 process 方法
        return super().process(mapped_data)
