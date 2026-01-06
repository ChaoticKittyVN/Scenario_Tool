"""
基于字典的句子生成器基类
专门为需要返回字典列表的引擎（如Utage）提供字典处理辅助方法
"""
from typing import List, Dict, Any, Optional
from core.base_sentence_generator import BaseSentenceGenerator


class DictBasedSentenceGenerator(BaseSentenceGenerator):
    """
    基于字典的句子生成器基类
    继承自BaseSentenceGenerator，添加字典处理辅助方法
    
    适用于返回 List[Dict[str, Any]] 的生成器（如Utage引擎）
    """

    def __init__(self, translator, engine_config):
        """
        初始化生成器并自动构建缓存
        
        Args:
            translator: 参数翻译器
            engine_config: 引擎配置
        """
        super().__init__(translator, engine_config)
        # 自动构建字段名缓存（从param_config中提取所有带key的配置）
        self._field_cache = self._build_field_cache()
        # 自动构建配置缓存（提取常用配置项）
        self._config_cache = self._build_config_cache()

    def _build_field_cache(self) -> Dict[str, str]:
        """
        自动从param_config中构建字段名缓存
        
        Returns:
            Dict[param_name, field_name]: 参数字段名到目标字段名的映射
        """
        cache = {}
        for param_name, param_cfg in self.param_config.items():
            if isinstance(param_cfg, dict) and "key" in param_cfg:
                cache[param_name] = param_cfg["key"]
        return cache

    def _build_config_cache(self) -> Dict[str, Dict[str, Any]]:
        """
        自动构建配置缓存（用于缓存stop_format、format等常用配置）
        
        Returns:
            Dict[param_name, config_dict]: 参数配置缓存
        """
        cache = {}
        for param_name, param_cfg in self.param_config.items():
            if not isinstance(param_cfg, dict):
                continue
            # 提取需要缓存的配置项
            cached_config = {}
            for key in ["stop_format", "format", "key", "default", "match_word"]:
                if key in param_cfg:
                    cached_config[key] = param_cfg[key]
            if cached_config:
                cache[param_name] = cached_config
        return cache

    def get_cached_field(self, param_name: str, default: Optional[str] = None) -> Optional[str]:
        """
        获取缓存的字段名
        
        Args:
            param_name: 参数名称
            default: 默认字段名（如果缓存中没有）
        
        Returns:
            字段名
        """
        return self._field_cache.get(param_name, default)

    def get_cached_config(self, param_name: str) -> Dict[str, Any]:
        """
        获取缓存的配置
        
        Args:
            param_name: 参数名称
        
        Returns:
            配置字典
        """
        return self._config_cache.get(param_name, {})

    def create_command_dict(self, command: str = "") -> Dict[str, Any]:
        """
        创建命令字典

        Args:
            command: 命令名称（可选）

        Returns:
            Dict[str, Any]: 新的命令字典
        """
        line = {}
        if command:
            line["Command"] = command
        return line

    def set_command(self, line: Dict[str, Any], command: str):
        """
        设置Command字段

        Args:
            line: 命令字典
            command: 命令名称
        """
        self._set_field(line, "Command", command)

    def _set_field(self, line: Dict[str, Any], field_name: str, value: Any):
        """
        设置字典字段（内部方法）

        Args:
            line: 命令字典
            field_name: 字段名称（如 "Arg1", "Text", "Command" 等）
            value: 字段值
        """
        line[field_name] = value

    def set_text(self, line: Dict[str, Any], text: str):
        """
        设置Text字段

        Args:
            line: 命令字典
            text: 文本内容
        """
        self._set_field(line, "Text", text)

    def set_param_from_config(
        self,
        line: Dict[str, Any],
        param_name: str,
        data: Dict[str, Any],
        default_key: Optional[str] = None
    ):
        """
        根据param_config中的key配置设置字段（推荐使用）
        
        如果param_config中配置了key，则使用该key；否则使用default_key或参数名本身

        Args:
            line: 命令字典
            param_name: 参数名称
            data: 数据字典
            default_key: 默认字段名（如果param_config中没有配置key）
        """
        if self.exists_param(param_name, data):
            value = self.get_value(param_name, data)
            if value:
                param_cfg = self.param_config.get(param_name, {})
                field_name = param_cfg.get("key", default_key or param_name)
                if field_name:
                    self._set_field(line, field_name, value)

    def set_param_if_exists(
        self,
        line: Dict[str, Any],
        param_name: str,
        data: Dict[str, Any],
        default_key: Optional[str] = None
    ):
        """
        如果参数存在且有值，则根据param_config中的key配置设置字段

        Args:
            line: 命令字典
            param_name: 参数名称
            data: 数据字典
            default_key: 默认字段名（如果param_config中没有配置key）
        """
        self.set_param_from_config(line, param_name, data, default_key)

    def _set_param_fast(
        self,
        line: Dict[str, Any],
        param_name: str,
        data: Dict[str, Any],
        field_name: Optional[str] = None
    ):
        """
        快速设置参数字段（性能优化版本，自动使用缓存的字段名）
        
        直接使用缓存的字段名，减少字典查找和方法调用开销

        Args:
            line: 命令字典
            param_name: 参数名称
            data: 数据字典
            field_name: 目标字段名（如果为None，则从缓存中自动获取）
        """
        if param_name not in data:
            return
        
        value = data[param_name]
        if not value:
            return
        
        # 优先使用传入的field_name，否则从缓存中获取，最后使用参数名本身
        if field_name is None:
            field_name = self._field_cache.get(param_name, param_name)
        
        # 直接设置字段，避免方法调用
        line[field_name] = str(value) if value else value


    def merge_dicts(self, *dicts: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并多个字典（后面的字典会覆盖前面的）

        Args:
            *dicts: 要合并的字典

        Returns:
            Dict[str, Any]: 合并后的字典
        """
        result = {}
        for d in dicts:
            if d:
                result.update(d)
        return result

    def process(self, data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """
        处理参数并生成命令字典列表（管道模式）

        Args:
            data: 参数字典

        Returns:
            Optional[List[Dict[str, Any]]]: 生成的命令字典列表，如果无法处理则返回 None
        """
        # 子类必须实现此方法
        raise NotImplementedError("子类必须实现process方法")

