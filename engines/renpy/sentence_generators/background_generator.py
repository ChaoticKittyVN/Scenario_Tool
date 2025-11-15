from core.base_sentence_generator import BaseSentenceGenerator

class BackgroundGenerator(BaseSentenceGenerator):

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
            "EventVarient": {
            },
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
                "match_word": "empty",
                "format_matched": ""
            },
            "WithAtr": {
                "format": "({value})"
            },
            "ATLType":{
            }
        }        
    
    @property
    def category(self):
        return "Background"


    
    @property
    def priority(self) -> int:
        return 200

    def process(self, data):
        """构建场景命令"""
        # 检查是否有足够的上下文生成场景命令
        if not self.can_process(data):
            return

        data = self.do_translate(data)

        lines = []


        if self.exsits_param("Background", data) or self.exsits_param("Event", data):
            line = ""
            background = self.get_value("Background", data)
            event = self.get_value("Event", data)

            # 构建场景命令
            command = self.get_value_default("Command", data) + " "
            image = background or event

            # 添加事件属性（差分）
            varient = self.get_value("Varient", data)
            if varient:
                image += f" {varient}"

            # 添加位置
            at = self.get_sentence("At", data)

            # 添加图层
            onlayer = self.get_sentence("Onlayer", data)

            # 添加过渡效果
            transition = self.get_value("With", data)
            if transition != "empty":
                transition = self.get_sentence_default("With", data)
                with_atr = self.get_sentence("WithAtr", data)
                if with_atr:
                    transition += with_atr
            else:
                transition = ""

            # 构建最终命令
            line = f"{command}{image}{at}{onlayer}{transition}"

            if self.exsits_param("ATLType", data):
                line = f"{line}:"

            lines.append(line)




        return lines
