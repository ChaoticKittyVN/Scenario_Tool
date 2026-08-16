"""
Utage Background Generator
生成背景、事件图和背景控制命令。
"""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from core.logger import get_logger
from core.scenario_state.effects import VisualEffectType, VisualStateEffect
from engines.utage.generator_base import UtageCommand, UtageGeneratorBase


logger = get_logger()


class BackgroundAction(str, Enum):
    """Resolved Utage background operation types."""

    SHOW = "show"
    HIDE = "hide"
    MOVE_LAYER = "move_layer"


@dataclass(frozen=True)
class BackgroundOperation:
    """Normalized background operation shared by rendering and state analysis."""

    action: BackgroundAction
    resource_type: str
    resource: str = ""
    layer: str = ""
    x: str = ""
    y: str = ""
    fade: str = ""
    wait_type: str = ""
    preserve_local: bool = False


class BackgroundGenerator(UtageGeneratorBase):
    """背景生成器。"""

    COMMAND_HIDE = "隐藏"
    COMMAND_CHANGE_LAYER = "换图层"
    DEFAULT_LAYER = "BG"
    DEFAULT_LAYER_ALIASES = {"默认", "Bg", "BG"}

    resource_config = {
        "resource_type": "Background",
        "resource_category": "图片",
        "main_param": "Background",
        "part_params": [],
        "separator": " ",
        "folder": "images/Background/",
    }

    resource_config_event = {
        "resource_type": "Event",
        "resource_category": "图片",
        "main_param": "Event",
        "part_params": ["EventVariant"],
        "separator": " ",
        "folder": "images/Event/",
    }

    param_config = {
        "BgCommand": {
            "validate_type": "BgCommand",
        },
        "Bg": {
            "validate_type": "Background",
            "key": "Arg1",
        },
        "BgAtr": {},
        "BgEvent": {
            "validate_type": "Event",
            "key": "Arg1",
        },
        "BgEventAtr": {},
        "BgLayer": {
            "validate_type": "Layer",
            "key": "Arg3",
        },
        "BgX": {
            "key": "Arg4",
        },
        "BgY": {
            "key": "Arg5",
        },
        "BgFade": {
            "key": "Arg6",
            "default": "1",
        },
        "WaitType": {
            "key": "WaitType",
            "translate_type": "WaitType",
        },
    }

    @property
    def category(self):
        return "Background"

    @property
    def priority(self) -> int:
        return 200

    def can_process(self, data: Dict[str, Any]) -> bool:
        return any(self.exists_param(name, data) for name in ("BgCommand", "Bg", "BgEvent"))

    def process(self, data: Dict[str, Any]) -> Optional[list]:
        """根据一行表格参数生成 Utage 背景命令。"""
        operation = self.resolve(data)
        return self.render(operation) if operation else None

    def resolve(self, data: Dict[str, Any]) -> Optional[BackgroundOperation]:
        """Resolve table parameters into one semantic background operation."""
        if not data or not self.can_process(data):
            return None

        data = self.do_translate(data)
        bg_command = self.get_value("BgCommand", data)

        if bg_command:
            return self._resolve_control_command(bg_command, data)

        return self._resolve_display_command(data)

    def _resolve_control_command(
        self,
        bg_command: str,
        data: Dict[str, Any],
    ) -> Optional[BackgroundOperation]:
        if bg_command == self.COMMAND_HIDE:
            return self._resolve_hide_command(data)

        if bg_command == self.COMMAND_CHANGE_LAYER:
            return self._resolve_change_layer_command(data)

        logger.warning("不支持的背景指令: %s", bg_command)
        return None

    def _resolve_hide_command(self, data: Dict[str, Any]) -> Optional[BackgroundOperation]:
        has_background = bool(self.get_value("Bg", data))
        has_event = bool(self.get_value("BgEvent", data))

        if has_background == has_event:
            logger.warning("BgCommand=隐藏 时必须且只能填写 Bg 或 BgEvent 其中一项")
            return None

        return BackgroundOperation(
            action=BackgroundAction.HIDE,
            resource_type="Event" if has_event else "Background",
            fade=self.get_value("BgFade", data, use_default=True),
            wait_type=self.get_value("WaitType", data),
        )

    def _resolve_change_layer_command(
        self,
        data: Dict[str, Any],
    ) -> Optional[BackgroundOperation]:
        target_layer = self.get_value("BgLayer", data)
        if not target_layer:
            logger.warning("BgCommand=换图层 时必须填写目标 BgLayer")
            return None

        if self.get_value("Bg", data) or self.get_value("BgEvent", data):
            logger.warning("BgCommand=换图层 时 Bg/BgEvent 不会重新加载资源，将忽略其值")

        if target_layer in self.DEFAULT_LAYER_ALIASES:
            target_layer = self.DEFAULT_LAYER

        return BackgroundOperation(
            action=BackgroundAction.MOVE_LAYER,
            resource_type="Background",
            layer=target_layer,
            wait_type=self.get_value("WaitType", data),
            preserve_local=True,
        )

    def _resolve_display_command(
        self,
        data: Dict[str, Any],
    ) -> Optional[BackgroundOperation]:
        background = self.get_value("Bg", data)
        event = self.get_value("BgEvent", data)

        if background:
            resource_type = "Background"
            image = background + self.get_value("BgAtr", data)
        elif event:
            resource_type = "Event"
            image = event + self.get_value("BgEventAtr", data)
        else:
            return None

        is_off = background == "off" or event == "off"
        return BackgroundOperation(
            action=BackgroundAction.HIDE if is_off else BackgroundAction.SHOW,
            resource_type=resource_type,
            resource="" if is_off else image,
            layer=self.get_value("BgLayer", data),
            x=self.get_value("BgX", data),
            y=self.get_value("BgY", data),
            fade=self.get_value("BgFade", data, use_default=True),
            wait_type=self.get_value("WaitType", data),
        )

    def render(self, operation: BackgroundOperation) -> List[UtageCommand]:
        """Render a resolved operation to the existing Utage row contract."""
        if operation.action == BackgroundAction.MOVE_LAYER:
            line = self.create_command("ChangeLayer")
            line["Arg1"] = "BG"
            line["Arg2"] = "KeepLocal"
            line["Arg3"] = operation.layer
        else:
            command = "BgEvent" if operation.resource_type == "Event" else "Bg"
            if operation.action == BackgroundAction.HIDE:
                command += "Off"

            line = self.create_command(command)
            if operation.action == BackgroundAction.SHOW:
                line["Arg1"] = operation.resource
                self._set_resolved_value(line, "Arg3", operation.layer)
                self._set_resolved_value(line, "Arg4", operation.x)
                self._set_resolved_value(line, "Arg5", operation.y)
            self._set_resolved_value(line, "Arg6", operation.fade)

        self._set_resolved_value(line, "WaitType", operation.wait_type)
        return [line]

    def state_effects(
        self,
        data: Dict[str, Any],
        context: Optional[Any] = None,
    ) -> List[VisualStateEffect]:
        """Describe the visual state change caused by this background row."""
        operation = self.resolve(data)
        if not operation:
            return []

        effect_type = {
            BackgroundAction.SHOW: VisualEffectType.SHOW,
            BackgroundAction.HIDE: VisualEffectType.HIDE,
            BackgroundAction.MOVE_LAYER: VisualEffectType.MOVE_LAYER,
        }[operation.action]

        return [
            VisualStateEffect(
                effect_type=effect_type,
                resource_type=operation.resource_type,
                resource=operation.resource,
                layer=operation.layer or self.DEFAULT_LAYER,
                x=operation.x,
                y=operation.y,
                transition_duration=operation.fade,
                wait_type=operation.wait_type,
                preserve_local=operation.preserve_local,
                context=context,
            )
        ]

    @staticmethod
    def _set_resolved_value(line: UtageCommand, field_name: str, value: str) -> None:
        if value:
            line[field_name] = value
