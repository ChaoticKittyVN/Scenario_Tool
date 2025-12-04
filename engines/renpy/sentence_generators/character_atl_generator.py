"""
Ren'Py Character ATL Generator
生成角色 ATL 动画命令（继承自 ATLGenerator）
"""
from .atl_generator import ATLGenerator

class SpriteATLGenerator(ATLGenerator):

    param_config = {
        "SpriteATLType": ATLGenerator.param_config["ATLType"],
        "SpriteATLWarp": ATLGenerator.param_config["ATLWarp"],
        "SpriteATLTime": ATLGenerator.param_config["ATLTime"],
        "SpriteATLTransform": ATLGenerator.param_config["ATLTransform"],
        "SpriteATLValue": ATLGenerator.param_config["ATLValue"],
    }

    @property
    def category(self) -> str:
        return "SpriteATL"

    @property
    def priority(self) -> int:
        return 251