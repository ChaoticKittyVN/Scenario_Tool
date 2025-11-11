from core.base_sentence_generator import BaseSentenceGenerator
from engines.naninovel.param_processor import ParamProcessor as pm

param_processor = pm()

class HiedeGenerator(BaseSentenceGenerator):
    
    @property
    def default_param(self) -> dict[str, str]:
        return {
            "Hide": "",
            "HideWait": "",
            "HideChars": "",
            "HideCharsWait": ""
        }
    
    @property
    def category(self):
        return "Hide"

    @property
    def priority(self) -> int:
        return 400

    def process(self, data):
        if not self.can_process(data):
            return

        data = self.do_translate(data)


        """构建隐藏和转场命令"""
        results = []
        
        # 处理隐藏命令
        if "Hide" in data:
            hide_target = data.get("Hide")
            wait = param_processor._process_wait_parameter(data.get("HideWait"))
            result = f"@hide {hide_target}{wait}"
            results.append(result)
        
        # 处理隐藏角色命令
        if "HideChars" in data:
            wait = param_processor._process_wait_parameter(data.get("HideCharsWait"))
            result = f"@hideChars{wait}"
            results.append(result)

        return results