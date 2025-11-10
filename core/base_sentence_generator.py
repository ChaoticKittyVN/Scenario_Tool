# core/base_sentence_generator.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseSentenceGenerator(ABC):
    """句子生成器基类 - 管道模式"""
    
    def __init__(self, format_config, translator):
        self.format_config = format_config
        self.translator = translator

    @property
    @abstractmethod
    def category(self) -> str:
        """返回生成器处理的句子类型"""
        pass

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

    @property
    @abstractmethod
    def default_param(self) -> dict[str, str]:
        """默认参数值词典"""
        pass


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
            translate_type = self.format_config.get(name).get("translate_type")

            if translate_type:
                new_value = self.translator.translate(translate_type, value)
                new_data[name] = new_value

            elif self.format_config.get(name).get("translate_types"):
                for translate_type in self.format_config.get(name).get("translate_types"):
                    if value in self.translator.mappings[translate_type]:
                        new_value = self.translator.translate(translate_type, value)
                        new_data[name] = new_value
                        break
            else:
                continue

        return new_data

    def get_value(self, value):
        return value if value else ""
    
    def get_value2(self, name, data):
        if name in data:
            return data.get(name)
        else:
            return ""
        
    def get_int(self, num : str):
        num = str(num)
        try:
            return int(float(num))
        except:
            print(f"警告：{num}不是支持的数字格式") 
            return num