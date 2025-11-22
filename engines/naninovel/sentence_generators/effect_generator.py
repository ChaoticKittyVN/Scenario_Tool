from core.base_sentence_generator import BaseSentenceGenerator


class EffectGenerator(BaseSentenceGenerator):
    param_config = {
        "PackedEffect": {
            "translate_type": "PackedEffect"
        },

        "Effect": {
            "translate_type": "Effect"
        },

        "EffectId": {
            "translate_type": "Id",
        },

        "EffectAtr1": {
        },

        "EffectAtr2": {
        },

        "Power": {
            "format": " power:{value}"
        },

        "EffectTime": {
            "format": " time:{value}",
            "default": "1"
        },
        "EffectWait": {
            "format": " wait:{value}",
        },
    }
    @property
    def category(self):
        return "Effect"

    @property
    def priority(self) -> int:
        return 120

    def process(self, data):
        if not self.can_process(data):
            return
        
        data = self.do_translate(data)

        lines = []

        if self.exists_param("PackedEffect", data):
            packed_effect = self.get_value("PackedEffect", data)
            return [packed_effect]
        
        if self.exists_param("Effect", data):
            effect = self.get_value("Effect", data)
            id_ = self.get_value("EffectId", data)

            time = self.get_sentence("EffectTime", data)
            wait = self.get_sentence("EffectWait", data)
            match effect:
                case "blur":
                    power = self.get_sentence("EffectPower", data)
                    line = f"@blur {id_}{power}{wait}{time}"
                case "shake":
                    power = self.get_sentence("EffectPower", data)
                    count = f" count:{self.get_value('EffectAtr1', data)}"
                    line = f"@shake {id_}{power}{count}{wait}{time}"
                case _:
                    line = ""

            lines.append(line)

        return lines