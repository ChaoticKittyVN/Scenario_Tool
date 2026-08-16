"""Engine-independent state effects used by scenario analysis."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class VisualEffectType(str, Enum):
    """Supported visual state mutations."""

    SHOW = "show"
    HIDE = "hide"
    MOVE_LAYER = "move_layer"


@dataclass(frozen=True)
class VisualStateEffect:
    """One deterministic change to a visual resource state."""

    effect_type: VisualEffectType
    resource_type: str
    resource: str = ""
    layer: str = ""
    x: str = ""
    y: str = ""
    transition_duration: str = ""
    wait_type: str = ""
    preserve_local: bool = False
    context: Optional[Any] = None
