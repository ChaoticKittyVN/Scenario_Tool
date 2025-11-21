"""
Ren'Py ATL Generator
生成 ATL (Animation and Transformation Language) 动画命令
"""
from core.base_sentence_generator import BaseSentenceGenerator


class ATLGenerator(BaseSentenceGenerator):
    """ATL 动画生成器"""

    param_config = {
        "ATLType": {
            "translate_type": "ATLtype",
        },
        "ATLWarp": {
            "translate_type": "Warp",
            "default": "linear"
        },
        "ATLTime": {
            "default": "1.0"
        },
        "ATLTransform": {
            "translate_type": "Transform"
        },
        "ATLValue": {},
    }

    @property
    def category(self) -> str:
        return "ATL"

    @property
    def priority(self) -> int:
        return 201

    def process(self, data):
        """
        处理 ATL 参数

        Args:
            data: 参数字典

        Returns:
            List[str]: 生成的 ATL 命令
        """
        if not self.can_process(data):
            return None

        data = self.do_translate(data)
        param_names = list(self.param_config.keys())

        atl_type = self.get_value(param_names[0], data)

        if atl_type == "变换":
            transform = self.get_value(param_names[3], data)
            line = f"    {transform}"
        elif atl_type == "动画":
            warp = self.get_value(param_names[1], data, use_default=True)
            time = self.get_value(param_names[2], data, use_default=True)
            transform = self.get_value(param_names[3], data)
            line = f"    {warp} {time} {transform}"
        elif atl_type == "等待":
            time = self.get_value(param_names[2], data, use_default=True)
            line = f"    pause {time}"
        elif atl_type == "直接输入":
            value = self.get_value(param_names[4], data)
            line = f"    {value}"
        elif atl_type == "自定义动画":
            warp = self.get_value(param_names[1], data, use_default=True)
            time = self.get_value(param_names[2], data, use_default=True)
            value = self.get_value(param_names[4], data)
            line = f"    {warp} {time} {value}"
        elif atl_type == "动画开始":
            line = "    animate"
        else:
            line = ""

        return [line] if line else []
