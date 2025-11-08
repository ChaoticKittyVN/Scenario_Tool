from abc import ABC, abstractmethod
from typing import List, Dict, Any
import os
import glob

class BaseProjectFilesValidator(ABC):
    """项目文件验证器基类"""

    def __init__(self, format_config, translator):
        self.format_config = format_config
        self.translator = translator

    @property
    @abstractmethod
    def source_path(self) -> str:
        """资源库路径"""
        pass
        
    @property
    @abstractmethod
    def project_path(self) -> str:
        """项目库路径"""
        pass

    @property
    @abstractmethod
    def path_dict(self) -> dict:
        """文件类型路径词典"""
        pass

    @property
    @abstractmethod
    def param_names(self) -> list:
        """需要抓取的参数类型"""
        pass

    @abstractmethod
    def extract_filenames_from_params(self, params: Dict[str, Any]) -> List[str]:
        """
        从参数中提取文件名
        这个方法由子类实现，因为不同引擎的文件名提取逻辑可能不同
        
        Args:
            params: 参数字典
            
        Returns:
            List[str]: 提取出的文件名列表（不带扩展名）
        """
        pass

    def can_process(self, data):
        """判断是否可以处理数据"""
        if data:
            return True
        else:
            return False

    def do_translate(self, row_data: dict):
        """翻译数据（从父类继承）"""
        new_data = row_data
        for name, value in row_data.items():
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
    
    def is_same_list(self, source_list: list, project_list: list) -> bool:
        """比较两个列表是否相同（忽略顺序）"""
        return sorted(source_list) == sorted(project_list)

    def search_files_in_source(self, filenames: List[str], file_types: List[str] = None) -> Dict[str, str]:
        """
        在资源库中搜索文件，返回带扩展名的完整文件名
        
        Args:
            filenames: 文件名列表（不带扩展名）
            file_types: 要搜索的文件类型列表，如果为None则搜索所有类型
            
        Returns:
            Dict[str, str]: 文件名映射 {原始文件名: 带扩展名的完整文件名}
        """
        result = {}
        
        # 如果没有指定文件类型，搜索所有类型
        if file_types is None:
            file_types = list(self.path_dict.keys())
        
        for filename in filenames:
            if not filename:  # 跳过空文件名
                continue
                
            found_file = self._find_file_in_source(filename, file_types)
            if found_file:
                result[filename] = found_file
            else:
                # 记录未找到的文件
                result[filename] = None
                
        return result

    def _find_file_in_source(self, filename: str, file_types: List[str]) -> str:
        """
        在资源库中查找指定文件
        
        Args:
            filename: 文件名（不带扩展名）
            file_types: 要搜索的文件类型列表
            
        Returns:
            str: 找到的完整文件名，如果未找到返回None
        """
        for file_type in file_types:
            if file_type not in self.path_dict:
                continue
                
            # 构建搜索路径
            search_dir = os.path.join(self.source_path, self.path_dict[file_type])
            
            # 检查目录是否存在
            if not os.path.exists(search_dir):
                continue
                
            # 使用glob搜索匹配的文件（不区分大小写）
            pattern = os.path.join(search_dir, f"{filename}.*")
            matching_files = glob.glob(pattern)
            
            # 尝试精确匹配（不区分大小写）
            for file_path in matching_files:
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                if base_name.lower() == filename.lower():
                    return os.path.basename(file_path)  # 返回带扩展名的文件名
        
        return None

    def get_used_files_from_params(self, params: Dict[str, Any]) -> Dict[str, str]:
        """
        从参数中提取使用的文件，并在资源库中搜索完整文件名
        
        Args:
            params: 参数字典
            
        Returns:
            Dict[str, str]: 文件名映射 {原始文件名: 带扩展名的完整文件名}
        """
        # 1. 提取文件名
        filenames = self.extract_filenames_from_params(params)
        
        # 2. 在资源库中搜索完整文件名
        full_filenames = self.search_files_in_source(filenames)
        
        return full_filenames
    
    def get_target_columns(self) -> List[str]:
        """
        获取需要处理的列名
        
        Returns:
            List[str]: 需要处理的列名列表
        """
        # 默认实现：返回format_config中所有的键
        return list(self.format_config.keys())
    
    def get_file_type_for_column(self, column_name: str) -> str:
        """
        根据列名获取文件类型
        
        Args:
            column_name: 列名
            
        Returns:
            str: 文件类型
        """
        # 默认实现：直接使用列名作为文件类型
        # 子类可以覆盖这个方法，提供更准确的映射
        return column_name
        
