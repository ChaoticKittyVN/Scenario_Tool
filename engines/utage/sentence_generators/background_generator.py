"""
Utage Background Generator
生成背景和事件相关命令
"""
from typing import Any, Dict, Optional
from core.dict_based_sentence_generator import DictBasedSentenceGenerator


class BackgroundGenerator(DictBasedSentenceGenerator):
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
        "Bg": {
            "translate_type": "Background",
            "key": "Arg1"
        },
        "BgEvent": {
            "translate_type": "Event",
            "key": "Arg1"
        },
        "EventVarient": {
            "key": "Arg2"
        },
        "BgLayer": {
            "translate_type": "Layer",
            "key": "Arg3"
        },
        "BgX": {
            "key": "Arg4"
        },
        "BgY": {
            "key": "Arg5"
        },
        "BgFade": {
            "key": "Arg6",
            "default": "1.0"
        },
    }

    @property
    def category(self):
        return "Background"

    @property
    def priority(self) -> int:
        return 200

    def can_process(self, data: Dict[str, Any]) -> bool:
        return super().can_process(data) and (
            "Background" in data or "Event" in data
        )

    def process(self, data: Dict[str, Any]) -> Optional[list]:
        """
        构建场景命令（性能优化版本）

        Args:
            data: 参数字典

        Returns:
            List[Dict[str, Any]]: 生成的背景命令
        """
        # 快速检查是否可以处理
        if not data or ("Bg" not in data and "BgEvent" not in data):
            return None

        data = self.do_translate(data)
        
        # 直接获取值并转换为字符串，避免多次方法调用
        background = str(data.get("Bg", "")) if "Bg" in data else ""
        event = str(data.get("BgEvent", "")) if "BgEvent" in data else ""
        
        # 确定命令类型和图像
        if background:
            command = "Bg"
            image = background
        elif event:
            command = "BgEvent"
            image = event
        else:
            return None

        # 创建命令字典
        line = {}
        
        # 检查是否为关闭命令（直接字符串比较，避免创建列表）
        is_off = (background == "off" or event == "off")
        
        if is_off:
            line["Command"] = command + "Off"
            # 只设置BgFade（如果存在），自动使用缓存的字段名
            self._set_param_fast(line, "BgFade", data)
        else:
            line["Command"] = command
            line["Arg1"] = image

            # 批量设置可选参数（自动使用缓存的字段名）
            self._set_param_fast(line, "BgLayer", data)
            self._set_param_fast(line, "BgX", data)
            self._set_param_fast(line, "BgY", data)
            self._set_param_fast(line, "BgFade", data)

        return [line]
