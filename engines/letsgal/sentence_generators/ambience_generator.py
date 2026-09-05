"""Generate the table's independent ambience channel."""

from typing import Any, Dict, Optional

from engines.letsgal.generator_base import LetsGalGeneratorBase


class AmbienceGenerator(LetsGalGeneratorBase):
    """Keep ambience defaults independent while targeting LetsGal sound code.

    LetsGal's documented code layer exposes ``music``, ``sound`` and ``voice``
    rather than a separate ambience keyword. Ambience therefore uses a
    looping ``sound`` line; the separate generator keeps its default and
    future mapping isolated from ordinary one-shot sound effects.
    """

    resource_config = {
        "resource_type": "Ambience",
        "resource_category": "音频",
        "main_param": "Ambience",
        "part_params": [],
        "separator": "",
        "folder": "Audio/Ambience/",
    }

    param_config = {
        "Ambience": {},
        "Volume": {},
        "AudioFade": {},
        "AudioLoop": {},
        "AmbienceLoop": {},
    }

    @property
    def category(self) -> str:
        return "Ambience"

    @property
    def priority(self) -> int:
        return 110

    def can_process(self, data: Dict[str, Any]) -> bool:
        return not self.is_empty(data.get("Ambience"))

    def process(self, data: Dict[str, Any]) -> Optional[list[str]]:
        if not self.can_process(data):
            return None

        value = str(data["Ambience"]).strip()
        if value.lower() in {"stop", "停止", "关闭"}:
            line = "stop sound"
            fade = self.first_value(data, ("AudioFade",))
            if not self.is_empty(fade):
                line += f" fadeout {self.normalize_number(fade, field='AudioFade')}"
            return [line]

        tokens = ["play", "sound", value]
        volume = self.first_value(data, ("Volume",))
        if not self.is_empty(volume):
            tokens.extend(["volume", self.percent(volume)])

        loop = self.first_value(data, ("AmbienceLoop", "AudioLoop"))
        if self.normalize_bool(
            loop,
            default=bool(getattr(self.engine_config, "ambience_loop", True)),
        ):
            tokens.append("loop")

        fade = self.first_value(data, ("AudioFade",))
        if not self.is_empty(fade):
            tokens.extend(["fadein", self.normalize_number(fade, field="AudioFade")])
        return [" ".join(tokens)]
