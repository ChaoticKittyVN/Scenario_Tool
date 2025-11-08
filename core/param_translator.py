import importlib.util,os
from typing import Dict, Any
from core.config import MAPPINGS_FILE,VARIENT_MAPPINGS_FILE

class ParamTranslator:
    """
    参数翻译器类，用于加载参数映射并提供翻译功能
    """
    def __init__(self, module_file: str = "param_config/param_mappings.py", varient_module_file: str = "param_config/varient_mappings.py"):
        """
        初始化参数翻译器
        
        参数:
        module_file: 基础参数映射模块文件路径
        varient_module_file: 差分参数映射模块文件路径
        """
        self.module_file = module_file
        self.varient_module_file = varient_module_file
        self.mappings = self._load_mappings()
        self.varient_mappings = self._load_varient_mappings()
    
    def _load_mappings(self) -> Dict[str, Dict[str, str]]:
        """
        从Python模块加载映射字典
        
        返回:
        映射字典，如果加载失败则返回空字典
        """
        try:
            spec = importlib.util.spec_from_file_location("param_config/param_mappings.py", self.module_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module.PARAM_MAPPINGS
        except Exception as e:
            print(f"加载映射模块失败: {e}")
            return {}

    def _load_varient_mappings(self) -> Dict[str, Dict[str, str]]:
        """
        从Python模块加载差分映射字典
        
        返回:
        差分映射字典，如果加载失败则返回空字典
        """
        # 检查文件是否存在
        if not os.path.exists(self.varient_module_file):
            print(f"差分映射文件不存在: {self.varient_module_file}")
            return {}
            
        try:
            spec = importlib.util.spec_from_file_location("varient_mappings", self.varient_module_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, "VARIENT_MAPPINGS", {})
        except Exception as e:
            print(f"加载差分映射模块失败: {e}")
            return {}

    def translate(self, param_type: str, param: str) -> str:
        """
        翻译单个参数
        
        参数:
        param_type: 参数类型（如"Layer", "Transform", "Transition"）
        param: 要翻译的参数值
        
        返回:
        翻译后的参数值，如果找不到映射则返回原值
        """
        # 特殊处理Varient类型
        if param_type in self.mappings:
            if param in self.mappings[param_type]:
                return self.mappings[param_type][param]
            else:
                print(f"警告: 参数 '{param}' 在类型 '{param_type}' 的映射中未找到")
                return param
        else:
            print(f"警告: 参数类型 '{param_type}' 在映射中未找到")
            return param

    def _translate_varient(self, param: str, role: str = None) -> str:
        """
        翻译差分参数
        
        参数:
        param: 要翻译的差分参数值
        role: 角色名
        
        返回:
        翻译后的参数值
        """
        # 如果没有提供角色名，尝试从基础映射中查找
        if role is None:
            if "Varient" in self.mappings and param in self.mappings["Varient"]:
                return self.mappings["Varient"][param]
            else:
                print(f"警告: 差分参数 '{param}' 在基础映射中未找到，且未提供角色名")
                return param
        
        # 使用角色特定的映射
        if role in self.varient_mappings:
            if param in self.varient_mappings[role]:
                return self.varient_mappings[role][param]
            else:
                print(f"警告: 角色 '{role}' 的差分参数 '{param}' 在映射中未找到")
                return param
        else:
            print(f"警告: 角色 '{role}' 在差分映射中未找到")
            return param

    def translate_batch(self, param_type: str, params: list) -> list:
        """
        批量翻译参数
        
        参数:
        param_type: 参数类型
        params: 要翻译的参数列表
        
        返回:
        翻译后的参数列表
        """
        return [self.translate(param_type, param) for param in params]
    
    def get_available_types(self) -> list:
        """
        获取可用的参数类型列表
        
        返回:
        参数类型列表
        """
        return list(self.mappings.keys())
    
    def get_params_for_type(self, param_type: str) -> list:
        """
        获取指定参数类型的所有原始参数
        
        参数:
        param_type: 参数类型
        
        返回:
        原始参数列表，如果类型不存在则返回空列表
        """
        if param_type in self.mappings:
            return list(self.mappings[param_type].keys())
        return []
    
    def get_translations_for_type(self, param_type: str) -> list:
        """
        获取指定参数类型的所有翻译后参数
        
        参数:
        param_type: 参数类型
        
        返回:
        翻译后参数列表，如果类型不存在则返回空列表
        """
        if param_type in self.mappings:
            return list(self.mappings[param_type].values())
        return []


# 特定参数类型的翻译器类
class LayerTranslator(ParamTranslator):
    """Layer参数翻译器"""
    
    def translate_layer(self, param: str) -> str:
        """翻译Layer参数"""
        return self.translate("Layer", param)
    
    def get_layer_params(self) -> list:
        """获取所有Layer原始参数"""
        return self.get_params_for_type("Layer")
    
    def get_layer_translations(self) -> list:
        """获取所有Layer翻译后参数"""
        return self.get_translations_for_type("Layer")


class TransformTranslator(ParamTranslator):
    """Transform参数翻译器"""
    
    def translate_transform(self, param: str) -> str:
        """翻译Transform参数"""
        return self.translate("Transform", param)
    
    def get_transform_params(self) -> list:
        """获取所有Transform原始参数"""
        return self.get_params_for_type("Transform")
    
    def get_transform_translations(self) -> list:
        """获取所有Transform翻译后参数"""
        return self.get_translations_for_type("Transform")


class TransitionTranslator(ParamTranslator):
    """Transition参数翻译器"""
    
    def translate_transition(self, param: str) -> str:
        """翻译Transition参数"""
        return self.translate("Transition", param)
    
    def get_transition_params(self) -> list:
        """获取所有Transition原始参数"""
        return self.get_params_for_type("Transition")
    
    def get_transition_translations(self) -> list:
        """获取所有Transition翻译后参数"""
        return self.get_translations_for_type("Transition")