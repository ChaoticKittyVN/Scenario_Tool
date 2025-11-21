"""
Naninovel Background Generator
生成背景相关命令
"""
from core.base_sentence_generator import BaseSentenceGenerator


class BackgroundGenerator(BaseSentenceGenerator):
    """背景生成器"""

    param_config ={
        "TransBack": {
            "translate_type": "Background",
        },
        "Back": {
            "translate_type": "Background",
        },
        "Event": {
            "translate_type": "Background",
        },
        "BackID": {
            "translate_type": "Id",
            "format": " id:{value}",
            "default": "MainBackground"
        },
        "BackScale": {
            "format":" sacle:{value}"
        },
        "BackPos": {
            "format":" pos:{value}"
        },
        "BackVisible": {
            "format":" visible:{value}"
        },
        "BackWait": {
            "format":" wait:{value}"
        },
        "Dissolve": {
            "translate_type": "Transition",
            "format": " dissolve:{value}"
        },
        "DissolveParam": {
            "format": " params:{value}",
            "default": "90"
        },
        "BackTint": {
            "format":" tint:{value}",
        },
        "BackTime": {
            "format":" time:{value}",
            "default": "1.0"
        },
        "BackAnim": {
            "translate_type": "Background",
        },
        "BackAnimParam": {
            "translate_type": "Background",
        },
    }

    def __init__(self, translator, engine_config):
        super().__init__(translator, engine_config)

    @property
    def category(self):
        return "Background"

    @property
    def priority(self) -> int:
        return 200

    def process(self, data):
        """
        处理背景参数

        Args:
            data: 参数字典

        Returns:
            List[str]: 生成的背景命令
        """
        # 检查是否有足够的上下文生成场景命令
        if not self.can_process(data):
            return

        # data = self.do_translate(data)

        """构建场景命令"""
        # 检查是否有足够的上下文生成场景命令

        data = self.do_translate(data)

        background = self.get_value("Back", data)
        event = self.get_value("Event", data)

        if not background and not event:
            return None
        
        lines = []
        trans = self.get_value("TransBack", data)
        
        # 添加渐变遮罩
        dissolve = self.get_sentence("Dissolve", data)
        if dissolve:
            dissolve += self.get_sentence("DissolveParam", data, use_default=True)

        # 是否等待
        wait = self.get_sentence("BackWait", data)

        # 等待时间
        time = self.get_sentence("BackTime", data, use_default=True)

        if trans == "模块":
            command = "    "
        else:
            command = ""

        if "隐藏" in [background,event] or trans == "隐藏":
            command += "@hide "
            image = ""

            if background:
                # 添加图层
                id = self.get_value("BackID", data, use_default=True)
            else:
                id = "CG"

            if dissolve:
                image = f"{image}.Custom"
            
            line = f"{command}{image}{id}{dissolve}{wait}"

        else:
            command += "@back "
            # 构建场景命令
            if background:
                image = background
                id = self.get_value("BackID", data)
            else:
                image = event
                id = " id:CG"

            if dissolve:
                image = f"{image}.Custom"
            
            # 添加位置和缩放变换
            pos = self.get_sentence("BackPos", data)
            
            scale = self.get_sentence("BackScale", data)

            # 是否可见
            visible = self.get_sentence("BackVisible", data)

            tint = self.get_sentence("BackTint", data)

            line = f"{command}{image}{id}{pos}{scale}{visible}{tint}{dissolve}{wait}"

        # 构建最终命令
        if trans == "转场":
            lines.append(f"@trans{time}")
            lines.append(line)
        else:
            lines.append(f"{line}{time}")
        return lines
