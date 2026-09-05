"""Generate scene code for backgrounds and event CGs."""

from typing import Any, Dict, Optional

from engines.letsgal.generator_base import LetsGalGeneratorBase


class SceneGenerator(LetsGalGeneratorBase):
    """Backgrounds and event CGs share the ``scene`` code command."""

    resource_config = {
        "resource_type": "Background",
        "resource_category": "图片",
        "main_param": "Background",
        "part_params": [],
        "separator": "",
        "folder": "Backgrounds/",
    }
    resource_config_event = {
        "resource_type": "Event",
        "resource_category": "图片",
        "main_param": "Event",
        "part_params": ["EventVariant"],
        "separator": " ",
        "folder": "Backgrounds/",
    }

    param_config = {
        "Command": {},
        "Background": {},
        "Event": {},
        "EventVariant": {},
        "At": {},
        "Onlayer": {},
        "With": {},
        "WithAtr": {},
        "WithWait": {},
    }

    @property
    def category(self) -> str:
        return "Background"

    @property
    def priority(self) -> int:
        return 200

    def can_process(self, data: Dict[str, Any]) -> bool:
        return any(
            not self.is_empty(data.get(name)) for name in ("Background", "Event")
        )

    def _transition(self, data: Dict[str, Any]) -> str:
        config = self.engine_config
        transition = self.normalize_transition(
            self.first_value(
                data,
                ("With",),
                default=getattr(config, "default_transition", ""),
            )
        )
        if not transition:
            return ""

        duration = self.first_value(
            data,
            ("WithAtr",),
            default=getattr(config, "default_transition_duration", ""),
        )
        parts = ["with", transition]
        if not self.is_empty(duration):
            duration_text = str(duration).strip()
            if duration_text.startswith("(") and duration_text.endswith(")"):
                duration_text = duration_text[1:-1].strip()
            parts.extend(["duration", self.normalize_number(duration_text, field="WithAtr")])

        wait = self.normalize_bool(
            self.first_value(
                data,
                ("WithWait",),
                default=getattr(config, "default_transition_wait", False),
            ),
            default=False,
        )
        if wait:
            parts.append("wait")
        return " ".join(parts)

    def process(self, data: Dict[str, Any]) -> Optional[list[str]]:
        if not self.can_process(data):
            return None

        background = self.first_value(data, ("Background",))
        event = self.first_value(data, ("Event",))
        if background is not None and event is not None:
            raise ValueError("Background 与 Event 不能在同一行同时填写")

        resource = event if event is not None else background
        if event is not None:
            variant = self.first_value(data, ("EventVariant",))
            if not self.is_empty(variant):
                resource = f"{resource} {variant}"

        line = f"scene {resource}"
        position = self.first_value(data, ("At",))
        if not self.is_empty(position):
            line += f" at {self.normalize_position(position)}"
        transition = self._transition(data)
        if transition:
            line += f" {transition}"
        return [line]
