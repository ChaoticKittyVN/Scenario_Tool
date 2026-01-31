"""
Utage Camera Generator
生成镜头效果命令
"""
from typing import Any, Dict, Optional
from core.dict_based_sentence_generator import DictBasedSentenceGenerator


class CameraGenerator(DictBasedSentenceGenerator):
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
        self._set_param_fast(line, "ZoomCamera", data)
        self._set_param_fast(line, "Zoom", data)
        self._set_param_fast(line, "CameraX", data)
        self._set_param_fast(line, "CameraY", data)
        self._set_param_fast(line, "CameraTime", data)

        self._set_param_fast(line, "WaitType", data)
        return [line]
