"""Discover and load optional engine packages."""

from __future__ import annotations

import importlib
import pkgutil
import re
from types import ModuleType
from typing import Dict, Iterable, List, Optional

from core.engine_registry import EngineMetadata, EngineRegistry
from core.exceptions import EngineNotRegisteredError
from core.logger import get_logger


logger = get_logger()

_ENGINE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def discover_engine_names() -> List[str]:
    """Return engine package names that physically exist under ``engines``."""
    try:
        engines_package = importlib.import_module("engines")
    except ModuleNotFoundError:
        return []

    package_paths = getattr(engines_package, "__path__", None)
    if package_paths is None:
        return []
    return sorted(
        module_info.name
        for module_info in pkgutil.iter_modules(package_paths)
        if module_info.ispkg and not module_info.name.startswith("_")
    )


def _available_message(names: Iterable[str]) -> str:
    available = list(names)
    return ", ".join(available) if available else "无"


def _restore_module_registration(module: ModuleType, engine_name: str) -> None:
    """Restore decorator metadata when a cached module outlives the registry."""
    for value in vars(module).values():
        metadata = getattr(value, "__engine_metadata__", None)
        if isinstance(metadata, EngineMetadata) and metadata.name == engine_name:
            EngineRegistry.register(metadata)
            return


def load_engine(engine_name: str) -> EngineMetadata:
    """Load one installed engine and ensure that it is registered."""
    engine_name = str(engine_name)
    if not _ENGINE_NAME_PATTERN.fullmatch(engine_name):
        raise EngineNotRegisteredError(f"无效的引擎名称: {engine_name!r}")

    installed = discover_engine_names()
    if engine_name not in installed:
        raise EngineNotRegisteredError(
            f"引擎模块 '{engine_name}' 不存在。可用引擎: "
            f"{_available_message(installed)}"
        )

    try:
        module = importlib.import_module(f"engines.{engine_name}")
    except Exception as exc:
        raise EngineNotRegisteredError(
            f"加载引擎 '{engine_name}' 失败: {exc}"
        ) from exc

    if not EngineRegistry.is_registered(engine_name):
        _restore_module_registration(module, engine_name)
    if not EngineRegistry.is_registered(engine_name):
        raise EngineNotRegisteredError(
            f"引擎模块 'engines.{engine_name}' 未注册处理器"
        )
    return EngineRegistry.get(engine_name)


def filter_engine_names(enabled: Optional[Iterable[str]] = None) -> List[str]:
    """Apply an optional project allowlist to installed engine names."""
    installed = discover_engine_names()
    if not enabled:
        return installed
    enabled_names = [str(name) for name in enabled]
    return [name for name in enabled_names if name in installed]


def discover_engines(
    enabled: Optional[Iterable[str]] = None,
) -> Dict[str, EngineMetadata]:
    """Load discoverable engines, skipping broken optional packages."""
    installed = discover_engine_names()
    if enabled:
        for engine_name in enabled:
            if str(engine_name) not in installed:
                logger.warning(f"配置启用的引擎模块不存在: {engine_name}")
    discovered: Dict[str, EngineMetadata] = {}
    for engine_name in filter_engine_names(enabled):
        try:
            discovered[engine_name] = load_engine(engine_name)
        except EngineNotRegisteredError as exc:
            logger.warning(str(exc))
    return discovered


def select_default_engine_name(
    enabled: Optional[Iterable[str]] = None,
) -> str:
    """Choose a deterministic default from engines available to the project."""
    available = filter_engine_names(enabled)
    if not available:
        installed = discover_engine_names()
        raise EngineNotRegisteredError(
            "没有可用的引擎模块。已安装引擎: "
            f"{_available_message(installed)}"
        )
    return "renpy" if "renpy" in available else available[0]
