# core/base_sentence_generator.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseSentenceGenerator(ABC):
    """句子生成器基类 - 管道模式"""

    # @property
    # @abstractmethod
    # def self.param_config(self) -> dict[str, dict]:
    #     """参数属性词典"""
    #     pass

    # 类属性 - 参数配置
    param_config: Dict[str, Dict] = {}

    def __init__(self, translator):
        self.translator = translator

    @property
    @abstractmethod
    def category(self) -> str:
        """返回生成器处理的句子类型"""
        pass

    # @property
    # @abstractmethod
    # def necessary_param(self) -> list[str]:
    #     """返回生成器的必要参数列表"""
    #     pass

    @property
    def priority(self) -> int:
        """
        生成器执行优先级
        
        Returns:
            int: 优先级数字，越小越先执行
        """
        # 默认从文件名提取数字前缀
        import re
        filename = self.__class__.__module__.split('.')[-1]
        match = re.search(r'^(\d+)_', filename)
        if match:
            return int(match.group(1))
        return 999  # 没有前缀的放在最后




    @abstractmethod
    def process(self, params: Dict[str, Any]) -> List[str]:
        """
        处理参数并生成命令（管道模式）
        
        Args:
            params: 所有分组的参数字典 {type: {param: value}}
            context: 上下文管理器
            
        Returns:
            List[str]: 生成的命令列表
        """        
        pass

    def can_process(self, data):
        if data:
            return True
        else:
            return False

    def do_translate(self, row_data : dict):
        new_data = row_data
        for name,value in row_data.items():
            translate_type = self.param_config.get(name).get("translate_type")

            if translate_type:
                new_value = self.translator.translate(translate_type, value)
                new_data[name] = new_value

            elif self.param_config.get(name).get("translate_types"):
                for translate_type in self.param_config.get(name).get("translate_types"):
                    if value in self.translator.mappings[translate_type]:
                        new_value = self.translator.translate(translate_type, value)
                        new_data[name] = new_value
                        break
            else:
                continue

        return new_data

    # def get_value(self, value):
    #     return value if value else ""
    def get_int(self, num : str):
        num = str(num)
        try:
            return int(float(num))
        except:
            print(f"警告：{num}不是支持的数字格式") 
            return num
        
    def get_value2(self, name, data):
        return self.get_value_in_config(name, data)
        
    def get_format_in_config(self, name):
        return self.param_config.get(name).get("format")
    
    def get_value(self, name, data):
        if name in data:
            return data[name]
        else:
            return ""
        
    def get_value_default(self, name, data):
        if name in data:
            return str(data[name])
        elif self.param_config.get(name).get("default") is not None:
            return str(self.param_config.get(name).get("default"))
        else:
            return ""

    def get_sentence(self, name, data):
        format_str = self.param_config.get(name).get("format")
        if name in data:
            return format_str.format(value = data[name])
        else:
            return ""
        
    def get_sentence_default(self, name, data):
        format_str = self.param_config.get(name).get("format")
        value = self.get_value_default(name,data)
        return format_str.format(value = value)
        # if name in data:
        #     return format_str.format(value = data[name])
        # elif self.param_config.get(name).get("default") is not None:
        #     return format_str.format(value = self.param_config.get(name).get("default"))
        # else:
        #     return ""

    def exsits_param(self, name, data):
        return name in data