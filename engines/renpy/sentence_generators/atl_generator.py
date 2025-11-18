from core.base_sentence_generator import BaseSentenceGenerator

class ATLGenerator(BaseSentenceGenerator):

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
            "ATLValue": {
            },
        } 
    
    @property
    def category(self) -> str:
        return "ATL"

   
    
    @property
    def priority(self) -> int:
        return 201

    def process(self, data):
        if not self.can_process(data):
            return
        
        data = self.do_translate(data)
        param_names = list(self.param_config.keys())

        atl_type = self.get_value(param_names[0], data)

        match atl_type:
            case "变换":
                transform = self.get_value(param_names[3], data)
                line = f"    {transform}"
            case "动画":
                warp = self.get_value_default(param_names[1], data)
                time = self.get_value_default(param_names[2], data)
                transform = self.get_value(param_names[3], data)
                line = f"    {warp} {time} {transform}"
            case "等待":
                time = self.get_value_default(param_names[2], data)
                line = f"    pause {time}"
            case "直接输入":
                value = self.get_value(param_names[4], data)
                line = f"    {value}"
            case "自定义动画":
                warp = self.get_value_default(param_names[1], data)
                time = self.get_value_default(param_names[2], data)
                value = self.get_value(param_names[4], data)
                line = f"    {warp} {time} {value}"
            case "动画开始":
                line = "    animate"
            case _:
                line = ""
        # if self.exsits_param(param_names[0], data):
        #     line = self.get_value("ATL", data)

        return [line]