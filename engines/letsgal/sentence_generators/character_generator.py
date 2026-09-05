"""Generate LetsGal ``show`` and ``hide`` character code."""

from typing import Any, Dict, Optional

from engines.letsgal.generator_base import LetsGalGeneratorBase


class CharacterGenerator(LetsGalGeneratorBase):
    """Use repeated ``show`` lines for both initial display and updates."""

    resource_config = {
        "resource_type": "Character",
        "resource_category": "图片",
        "main_param": "Character",
        "part_params": ["Variant", "Atr1", "Atr2", "Atr3"],
        "separator": " ",
        "folder": "Characters/",
    }

    param_config = {
        "SpriteCommand": {},
        "CharacterCommand": {},
        "Character": {},
        "Sprite": {},
        "Variant": {},
        "Atr1": {},
        "Atr2": {},
        "Atr3": {},
        "SpriteAt": {},
        "SpriteOnlayer": {},
        "SpriteWith": {},
        "SpriteWithAtr": {},
        "SpriteWithWait": {},
        "Position": {},
    }

    _SHOW_ALIASES = {
        "show",
        "display",
        "showcharacter",
        "显示",
        "登场",
    }
    _HIDE_ALIASES = {
        "hide",
        "remove",
        "removecharacter",
        "隐藏",
        "退场",
    }

    @property
    def category(self) -> str:
        return "Character"

    @property
    def priority(self) -> int:
        return 250

    def can_process(self, data: Dict[str, Any]) -> bool:
        return any(
            not self.is_empty(data.get(name)) for name in ("Character", "Sprite")
        )

    def _command(self, value: Any) -> str:
        if self.is_empty(value):
            return "show"
        command = str(value).strip().lower()
        if command in self._SHOW_ALIASES:
            return "show"
        if command in self._HIDE_ALIASES:
            return "hide"
        raise ValueError("SpriteCommand 只能是 show/显示 或 hide/隐藏")

    def _transition(self, data: Dict[str, Any]) -> str:
        transition = self.normalize_transition(self.first_value(data, ("SpriteWith",)))
        if not transition:
            return ""
        parts = ["with", transition]
        duration = self.first_value(data, ("SpriteWithAtr",))
        if not self.is_empty(duration):
            duration_text = str(duration).strip()
            if duration_text.startswith("(") and duration_text.endswith(")"):
                duration_text = duration_text[1:-1].strip()
            parts.extend(
                [
                    "duration",
                    self.normalize_number(duration_text, field="SpriteWithAtr"),
                ]
            )
        if self.normalize_bool(self.first_value(data, ("SpriteWithWait",)), default=False):
            parts.append("wait")
        return " ".join(parts)

    def process(self, data: Dict[str, Any]) -> Optional[list[str]]:
        if not self.can_process(data):
            return None

        character = self.first_value(data, ("Character", "Sprite"))
        command = self._command(
            self.first_value(data, ("SpriteCommand", "CharacterCommand"))
        )
        if command == "hide":
            return [f"hide {character}"]

        tokens = ["show", str(character)]
        variant = self.first_value(data, ("Variant",))
        if not self.is_empty(variant):
            tokens.append(str(variant))

        for name in ("Atr1", "Atr2", "Atr3"):
            value = self.first_value(data, (name,))
            if not self.is_empty(value):
                tokens.append(str(value))

        position = self.first_value(data, ("Position", "SpriteAt"))
        if not self.is_empty(position):
            tokens.extend(["at", self.normalize_position(position)])

        transition = self._transition(data)
        if transition:
            tokens.extend(transition.split())
        return [" ".join(tokens)]
