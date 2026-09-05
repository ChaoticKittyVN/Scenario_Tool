"""Generate the documented LetsGal camera command."""

from typing import Any, Dict, Optional

from engines.letsgal.generator_base import LetsGalGeneratorBase


class CameraGenerator(LetsGalGeneratorBase):
    """Support the common x/y/zoom/duration/easing camera form."""

    param_config = {
        "Camera": {},
        "OffsetX": {},
        "OffsetY": {},
        "Zoom": {},
        "CameraDuration": {},
        "CameraTime": {},
        "CameraEasing": {},
        "CameraWait": {},
    }

    @property
    def category(self) -> str:
        return "Camera"

    @property
    def priority(self) -> int:
        return 150

    def can_process(self, data: Dict[str, Any]) -> bool:
        return any(
            not self.is_empty(data.get(name)) for name in self.param_config
        )

    def process(self, data: Dict[str, Any]) -> Optional[list[str]]:
        if not self.can_process(data):
            return None
        mode = str(data.get("Camera", "")).strip().lower()
        if mode in {"reset", "恢复镜头"}:
            return ["camera reset"]

        tokens = ["camera"]
        for name, keyword in (("OffsetX", "x"), ("OffsetY", "y"), ("Zoom", "zoom")):
            value = data.get(name)
            if not self.is_empty(value):
                tokens.extend([keyword, str(value).strip()])
        duration = self.first_value(data, ("CameraDuration", "CameraTime"))
        if not self.is_empty(duration):
            tokens.extend(
                ["duration", self.normalize_number(duration, field="CameraDuration")]
            )
        if not self.is_empty(data.get("CameraEasing")):
            tokens.extend(["easing", str(data["CameraEasing"]).strip()])
        if self.normalize_bool(data.get("CameraWait"), default=False):
            tokens.append("wait")
        return [" ".join(tokens)]
