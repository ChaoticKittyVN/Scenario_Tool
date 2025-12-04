"""
Ren'Py Background Generator
生成背景和事件相关命令
"""
from core.base_sentence_generator import BaseSentenceGenerator


class BackgroundGenerator(BaseSentenceGenerator):
    """背景生成器"""

    # 背景资源配置
    resource_config = {
        "resource_type": "Background",
        "resource_category": "图片",
        "main_param": "Background",
        "part_params": [],
        "separator": " ",
        "folder": "images/Background/"
    }

    # 事件CG资源配置
    resource_config_event = {
        "resource_type": "Event",
        "resource_category": "图片",
        "main_param": "Event",
        "part_params": ["EventVarient"],
        "separator": " ",
        "folder": "images/Event/"
    }

    param_config = {
        "Command": {
            "translate_type": "Command",
            "default": "show"
        },
        "Background": {
            "translate_type": "Background",
        },
        "Event": {
            "translate_type": "Event",
        },
        "EventVarient": {},
        "At": {
            "translate_type": "Transform",
            "format": " at {value}"
        },
        "Onlayer": {
            "translate_type": "Layer",
            "format": " onlayer {value}"
        },
        "With": {
            "translate_type": "Transition",
            "format": " with {value}",
            "default": "dissolve",
        },
        "WithAtr": {
            "format": "({value})"
        },
        "ATLType": {}
    }

    @property
    def category(self):
        return "Background"

    @property
    def priority(self) -> int:
        return 200

    def process(self, data):
        """
        构建场景命令

        Args:
            data: 参数字典

        Returns:
            List[str]: 生成的背景命令
        """
        if not self.can_process(data):
            return None

        data = self.do_translate(data)
        lines = []

        if self.exists_param("Background", data) or self.exists_param("Event", data):
            background = self.get_value("Background", data)
            event = self.get_value("Event", data)

            # 构建场景命令
            command = self.get_value("Command", data, use_default=True) + " "
            image = background or event

            # 添加事件属性（差分）
            varient = self.get_value("EventVarient", data)
            if varient:
                image += f" {varient}"

            # 添加位置
            at = self.get_sentence("At", data)

            # 添加图层
            onlayer = self.get_sentence("Onlayer", data)

            # 添加过渡效果
            transition = self.get_value("With", data)
            if transition != "empty":
                transition = self.get_sentence("With", data, use_default=True)
                with_atr = self.get_sentence("WithAtr", data, use_default=True)
                if with_atr:
                    transition += with_atr
            else:
                transition = ""

            # 构建最终命令
            line = f"{command}{image}{at}{onlayer}{transition}"

            if self.exists_param("ATLType", data):
                line = f"{line}:"

            lines.append(line)

        return lines
