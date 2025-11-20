"""
Naninovel 参数处理器
处理 Naninovel 引擎特定的参数格式
"""
from typing import Optional


class ParamProcessor:
    """参数处理器 - 实例化版本"""

    def __init__(self):
        """初始化参数处理器"""
        pass

    def _process_id_parameter(self, id_value) -> str:
        """处理ID参数"""
        return f" id:{id_value}" if id_value else ""

    def _process_pos_parameter(self, pos_value) -> str:
        """处理位置参数"""
        return f" pos:{pos_value}" if pos_value else ""

    def _process_position_parameter(self, position_value) -> str:
        """处理位置参数（世界坐标）"""
        return f" position:{position_value}" if position_value else ""

    def _process_scale_parameter(self, scale_value) -> str:
        """处理缩放参数"""
        return f" scale:{scale_value}" if scale_value else ""

    def _process_visible_parameter(self, visible_value) -> str:
        """处理可见性参数"""
        if visible_value == 0.0 or visible_value == "0" or visible_value == 0:
            return " visible:false"
        elif visible_value == 1.0 or visible_value == "1" or visible_value == 1:
            return " visible:true"
        else:
            return ""

    def _process_wait_parameter(self, wait_value) -> str:
        """处理等待参数"""
        if wait_value == 0.0 or wait_value == "0" or wait_value == 0:
            return " wait:false"
        elif wait_value == 1.0 or wait_value == "1" or wait_value == 1:
            return " wait:true"
        else:
            return ""

    def _process_time_parameter(self, time_value) -> str:
        """处理时间参数"""
        return f" time:{time_value}" if time_value else ""

    def _process_tint_parameter(self, tint_value) -> str:
        """处理色调参数"""
        return f" tint:{tint_value}" if tint_value else ""

    def _process_pose_parameter(self, pose_value) -> str:
        """处理姿势参数"""
        return f" pose:{pose_value}" if pose_value else ""

    def _process_dissolve_parameter(self, dissolve_value, dissolve_params=None) -> str:
        """处理溶解效果参数"""
        if not dissolve_value:
            return ""

        result = f" dissolve:{dissolve_value}"
        if dissolve_params:
            result += f" params:{dissolve_params}"

        return result

    def _process_printer_pos_parameter(self, pos_value) -> str:
        """处理打印机位置参数"""
        return f" pos:{pos_value}" if pos_value else ""
