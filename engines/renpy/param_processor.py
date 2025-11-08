# renpy引擎专用
import pandas as pd
from engines.renpy.engine_param_config import FORMAT_CONFIG
import core.param_translator as translator
translator = translator.ParamTranslator()

class ParamProcessor:
    def __init__(self):
        return
    
    # 辅助方法
    def _process_at_parameter(self, at_value):
        """处理位置参数"""
        return f" at {at_value}" if at_value else ""

    def _process_onlayer_parameter(self, onlayer_value):
        """处理图层参数"""
        return f" onlayer {onlayer_value}" if onlayer_value else ""

    def _process_transition_parameter(self, transition_value, transition_attr_value, default="dissolve"):
        """处理过渡效果参数"""
        
        if transition_value == "无":
            return ""
        
        # 处理过渡效果属性
        if transition_attr_value:

            if transition_value == "dissolve":
                transition = f"Dissolve({transition_attr_value})"
            else:
                transition = f"{transition_value}({transition_attr_value})"
        
        return f" with {transition}" if transition else ""

    def _process_atl_parameter(self,atl):
        """处理ATL参数"""
        return f":\n        {atl}" if atl else ""


    def clear_context(self):
        """清空上下文"""
        self.context = {}