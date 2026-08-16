"""
Utage Camera Generator
生成镜头效果命令
"""
from typing import Any, Dict, Optional
from engines.utage.generator_base import UtageGeneratorBase


class CameraGenerator(UtageGeneratorBase):
    """镜头效果生成器"""

    param_config = {
        "ZoomCamera": {
            "translate_type": "Camera",
            "default": "MainCamera",
            "key": "Arg1"
        },
        "Zoom": {
            "key": "Arg2"
        },
        "CameraX": {
            "key": "Arg3"
        },
        "CameraY": {
            "key": "Arg4"
        },
        "CameraTime": {
            "key": "Arg6",
            "default": "0.5"
        },
        "WaitType":{
            "key": "WaitType",
            "translate_type": "WaitType"
        }
    }

    @property
    def category(self):
        return "Camera"

    @property
    def priority(self) -> int:
        return 150

    def process(self, data: Dict[str, Any]) -> Optional[list]:
        """
        处理镜头效果参数

        Args:
            data: 参数字典

        Returns:
            List[str]: 生成的镜头效果命令
        """
        if not self.can_process(data):
            return None

        data = self.do_translate(data)

        line = {}
        self.set_param(line, "ZoomCamera", data)
        self.set_param(line, "Zoom", data)
        self.set_param(line, "CameraX", data)
        self.set_param(line, "CameraY", data)
        self.set_param(line, "CameraTime", data)

        self.set_wait_type(line, data)
        return [line]
