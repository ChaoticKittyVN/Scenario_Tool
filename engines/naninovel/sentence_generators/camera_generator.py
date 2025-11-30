from core.base_sentence_generator import BaseSentenceGenerator

class CameraGenerator(BaseSentenceGenerator):

    param_config = {   
        "Camera": {
            "validate_type": "Camera"
            },

        "Zoom": {
            "format": " zoom:{value}"
            },

        "OffsetX": {
            "default": "0",
            "format": " offset:{value}"
            },

        "OffsetY": {
            "default": "0",
            "format": ",{value}"
            },

        "CameraWait": {
            "format": " wait:{value}"
            },

        "CameraTime": {
            "format": " time:{value}",
            "default": "0"
            },
    }

    @property
    def category(self):
        return "Camera"

    @property
    def priority(self) -> int:
        return 140

    def process(self, data):
        """
        处理镜头参数

        Args:
            data: 参数字典

        Returns:
            List[str]: 生成的镜头命令
        """
        if not self.can_process(data):
            return None
        
        # data = self.do_translate(data)

        lines = []

        command_type = data.get("Camera")

        time = self.get_sentence("CameraTime", data)

        if command_type == "重置":
            lines.append("@trans")
            lines.append(f"    @camera offset:0,0 zoom:0 rotation:0,0,0{time}")
            return lines

        if command_type == "镜头":
            command = "@camera"
        else:
            command = "    @camera"

        if command_type == "切镜头":
            lines.append("@trans")

        zoom = self.get_sentence("Zoom", data)

        if self.exists_param("OffsetX", data) or self.exists_param("OffsetY", data):
            offset_x = self.get_sentence("OffsetX", data)
            offset_y = self.get_sentence("OffsetY", data)
            offset = f"{offset_x}{offset_y}"
        else:
            offset = ""
        
        wait = self.get_sentence("CameraWait", data)
        
        line = f"{command}{zoom}{offset}{wait}{time}"
        
        lines.append(line)

        return lines