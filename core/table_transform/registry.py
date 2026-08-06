"""Operation registration and optional plugin loading."""

from __future__ import annotations

import importlib
from typing import Dict, Type

from .base import TableOperation


class OperationRegistry:
    def __init__(self):
        self._operations: Dict[str, Type[TableOperation]] = {}

    def register(self, operation_class: Type[TableOperation], name: str | None = None) -> None:
        operation_name = name or operation_class.operation_type
        if not operation_name:
            raise ValueError("操作类型名称不能为空。")
        self._operations[operation_name] = operation_class

    def load_plugin(self, reference: str) -> None:
        if ":" not in reference:
            raise ValueError(f"插件必须使用 module:Class 格式: {reference}")
        module_name, class_name = reference.split(":", 1)
        module = importlib.import_module(module_name)
        operation_class = getattr(module, class_name)
        if not isinstance(operation_class, type) or not issubclass(operation_class, TableOperation):
            raise TypeError(f"插件不是 TableOperation 子类: {reference}")
        self.register(operation_class)

    def create(self, operation_type: str, operation_id: str, config: dict) -> TableOperation:
        operation_class = self._operations.get(operation_type)
        if operation_class is None:
            raise ValueError(f"未注册的表格操作: {operation_type}")
        return operation_class(operation_id, config)

    def names(self) -> list[str]:
        return sorted(self._operations)
