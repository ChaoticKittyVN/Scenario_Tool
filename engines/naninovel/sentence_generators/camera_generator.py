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

        "Toggle": {
            "format": " toggle:{value}",
            "translate_type": "CameraEffect"
        },

        "CameraWait": {
            "format": " wait:{value}"
            },

        "CameraTime": {
            "format": " time:{value}",
            "default": "0"
            },

        "Transition": {},
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

        command = ""

        if self.exists_param("Transition", data):
            command += "    "

        command += "@camera"

        if command_type == "重置":
            lines.append(f"{command} offset:0,0 zoom:0 rotation:0,0,0{time}")
            return lines

        zoom = self.get_sentence("Zoom", data)

        if self.exists_param("OffsetX", data) or self.exists_param("OffsetY", data):
            offset_x = self.get_sentence("OffsetX", data, use_default=True)
            offset_y = self.get_sentence("OffsetY", data, use_default=True)
            offset = f"{offset_x}{offset_y}"
        else:
            offset = ""
        
        wait = self.get_sentence("CameraWait", data).lower()

        if self.exists_param("Toggle", data):
            if self.get_value("Toggle", data) in ["关闭", "off"]:
                camera_effect = " set:*.false"
            else:
                camera_effect = self.get_sentence("Toggle", data)
        else:
            camera_effect = ""


        line = f"{command}{zoom}{offset}{camera_effect}{wait}{time}"
        
        lines.append(line)

        return lines
    def can_process(self, data):
        return self.exists_param("Camera", data)