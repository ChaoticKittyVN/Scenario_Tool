# naninovel引擎专用
import pandas as pd
from engines.naninovel.engine_param_config import FORMAT_CONFIG
import core.param_translator as translator
translator = translator.ParamTranslator()

class ParamProcessor:
    def __init__(self,):
        return

    def _build_hide_trans_command(self):
        """构建隐藏和转场命令"""
        results = []
        
        # 处理隐藏命令
        if "Hide" in self.context:
            hide_target = self.context.get("Hide")
            wait = self._process_wait_parameter("HideWait")
            result = f"@hide {hide_target}{wait}"
            results.append(result)
        
        # 处理隐藏角色命令
        if "HideChars" in self.context:
            hide_chars = self.context.get("HideChars")
            wait = self._process_wait_parameter("HideCharsWait")
            result = f"@hide {hide_chars}{wait}"
            results.append(result)
        
        # 处理转场命令（单句处理）
        if "Transition" in self.context:
            transition = self.context.get("Transition")
            result = f"@transition {transition}"
            results.append(result)
            
        # 处理电影命令（单句处理）
        if "Movie" in self.context:
            movie = self.context.get("Movie")
            result = f"@movie {movie}"
            results.append(result)
            
        return results

    def _build_text_command(self):
        """构建文本命令"""
        results = []
        
        # 处理打印机设置
        if "Printer" in self.context:
            printer = self.context.get("Printer")
            pos = self._process_printer_pos_parameter("PrinterPos")
            result = f"@printer {printer}{pos}"
            results.append(result)
        
        # 处理隐藏打印机命令
        if "HidePrinter" in self.context:
            result = "@hidePrinter"
            results.append(result)
        
        # 处理对话文本
        speaker = self.context.get("Speaker", "")
        text = self.context.get("Text", "")
        
        if text:
            if speaker:
                # 命令模式，直接写入naninovel脚本
                if speaker == "naninovel":
                    result = text
                # 有说话者和文本  
                else:
                    result = f'{speaker}: "{text}"'
            else:
                # 只有文本
                result = f'{text}'
            results.append(result)
        
        return results
    
    # 辅助方法
    def _process_id_parameter(self, id_value):
        """处理ID参数"""
        return f" id:{id_value}" if id_value else ""

    def _process_pos_parameter(self, pos_value):
        """处理位置参数"""
        return f" pos:{pos_value}" if pos_value else ""

    def _process_position_parameter(self, position_value):
        """处理位置参数（世界坐标）"""
        return f" position:{position_value}" if position_value else ""

    def _process_scale_parameter(self, scale_value):
        """处理缩放参数"""
        return f" scale:{scale_value}" if scale_value else ""

    def _process_visible_parameter(self, visible_value):
        """处理可见性参数"""
        if visible_value == 0.0:
            return " visible:false"
        elif visible_value == 1.0:
            return " visible:true"
        else:
            return ""

    def _process_wait_parameter(self, wait_value):
        """处理等待参数"""
        if wait_value == 0.0:
            return " wait:false"
        elif wait_value == 1.0:
            return " wait:true"
        else:
            return ""

    def _process_time_parameter(self, time_value):
        """处理时间参数"""
        return f" time:{time_value}" if time_value else ""

    def _process_tint_parameter(self, tint_value):
        """处理色调参数"""
        return f" tint:{tint_value}" if tint_value else ""

    def _process_pose_parameter(self, pose_value):
        """处理姿势参数"""
        return f" pose:{pose_value}" if pose_value else ""

    def _process_dissolve_parameter(self, dissolve_value, dissolve_params):
        """处理溶解效果参数"""
        
        if not dissolve_value:
            return ""
        
        result = f" dissolve:{dissolve_value}"
        if dissolve_params:
            result += f" params:{dissolve_params}"
            
        return result

    def _process_printer_pos_parameter(self, pos_value):
        """处理打印机位置参数"""
        return f" pos:{pos_value}" if pos_value else ""
    
    def clear_context(self):
        """清空上下文"""
        self.context = {}