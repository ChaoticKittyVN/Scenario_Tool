"""
Utage Direct Command Generator
生成直接命令
"""
from typing import Any, Dict, Optional
from engines.utage.generator_base import UtageGeneratorBase


class DirectCommandGenerator(UtageGeneratorBase):
    """直接命令生成器"""

    # 标记：独占模式 - 当此生成器成功处理时，其他生成器（除Text相关）应被跳过
    EXCLUSIVE_MODE = True

    param_config = {
        "DirectCommand": {
            "key": "Command",
        },
        "CommandValue": {
            "key": "Arg1"
        },
        "MacroParam1":{},
        "MacroParam2":{},
        # "Index": {}
    }

    @property
    def category(self):
        return "DirectCommand"

    @property
    def priority(self) -> int:
        return 0

    def can_process(self, data: Dict[str, Any]) -> bool:
        """检查是否有DirectCommand参数"""
        return self.exists_param("DirectCommand", data)

    def process(self, data: Dict[str, Any]) -> Optional[list]:
        """
        处理直接命令参数

        Args:
            data: 参数字典

        Returns:
            Dict[str, Any]: 生成的直接命令
        """
        if not self.can_process(data):
            return None

        line = {}

        command = self.get_value("DirectCommand", data)
        value = data.get("CommandValue", "")
        if command in ["Jump", "Label", "Selection"]:
            if command == "Label":
                line["Command"] = self._labelize(value)
            elif command == "Jump":
                self.set_param(line, "DirectCommand", data)
                line["Arg1"] = self._labelize(value)
            elif command == "Selection":
                self.set_param(line, "DirectCommand", data)
                # 选项跳转标签
                line["Arg1"] = self._labelize(value)

                # 选项条件式
                line["Arg2"] = self.get_value("MacroParam1", data)

                # 选项执行计算式
                line["Arg3"] = self.get_value("MacroParam2", data)

                # 选项文本
                line["Text"] = self.get_value("Text", data) if self.exists_param("Text", data) else value

        else:
            self.set_param(line, "CommandValue", data)
            self.set_param(line, "DirectCommand", data)

        return [line]
    
    def _labelize(self, label: str) -> str:
        """将标签转换为命令格式（如 Jump 或 Label 的参数）"""
        return str(f"*{label}")
