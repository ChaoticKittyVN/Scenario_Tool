from .atl_generator import ATLGenerator

class SpriteATLGenerator(ATLGenerator):

    param_config = {
        "SpriteATLType": ATLGenerator.param_config["ATLType"],
        "SpriteATLWarp": ATLGenerator.param_config["ATLWarp"],
        "SpriteATLTime": ATLGenerator.param_config["ATLTime"],
        "SpriteATLTransform": ATLGenerator.param_config["ATLTransform"],
        "SpriteATLValue": ATLGenerator.param_config["ATLValue"],
    }

    @property
    def category(self):
        return "SpriteATL"

    @property
    def priority(self) -> int:
        return 251

    # def process(self, data):
    #     if not self.can_process(data):
    #         return
        
    #     # data = self.do_translate(data)

    #     if self.exsits_param("SpriteATLtype", data):
    #         line = self.get_value("SpriteATL", data)

    #     return [line]