"""
Utage Camera Generator
生成镜头效果命令
"""
from typing import Any, Dict, Optional
from core.dict_based_sentence_generator import DictBasedSentenceGenerator


class CameraGenerator(DictBasedSentenceGenerator):
    """镜头效果生成器"""

    param_config = {
        "Camera": {
            "translate_type": "Camera"
        },
        "CameraLayer": {
            "translate_type": "Layer",
            "format": " {value}"
        },
        "CameraAt": {
            "translate_type": "Transform",
            "format": " at {value}"
        },
        "Zoom": {
            "format": " zoom {value}"
        },
        "OffsetX": {
            "format": " xoffset {value}"
        },
        "OffsetY": {
            "format": " yoffset {value}"
        },
        "CameraATL": {
        },
    }

    @property
    def category(self):
        return "Camera"

    @property
    def priority(self) -> int:
        return 150

    def process(self, data):
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

        camera = self.get_value("Camera", data)

        command = "camera"
        layer = self.get_sentence("CameraOnlayer", data)

        if camera == "transform":
            at = self.get_sentence("CameraAt", data)
            return [f"{command}{layer}{at}"]
        

        lines = []

        if camera == "move":
            zoom = self.get_sentence("Zoom", data)
            x = self.get_sentence("OffsetX", data)
            y = self.get_sentence("OffsetY", data)
            lines.append(f"{command}{layer}:")
            lines.append(f"   {zoom}{x}{y}")
            return lines

        if camera == "custom":
            custom = self.get_value("CameraATL", data)
            lines.append(f"{command}{layer}:")
            lines.append(f"    {custom}")
            return lines

        return ["camera"]
