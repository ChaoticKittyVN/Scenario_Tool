"""Generate direct-path LetsGal voice code."""

from typing import Any, Dict, Optional

from engines.letsgal.generator_base import LetsGalGeneratorBase


class VoiceGenerator(LetsGalGeneratorBase):
    """Voice is a path cell, not a translated resource identifier."""

    resource_config = {
        "resource_type": "Voice",
        "resource_category": "音频",
        "main_param": "Voice",
        "part_params": [],
        "separator": "",
        "folder": "Audio/Voice/",
    }

    param_config = {"Voice": {}}

    @property
    def category(self) -> str:
        return "Voice"

    @property
    def priority(self) -> int:
        return 890

    def process(self, data: Dict[str, Any]) -> Optional[list[str]]:
        if not self.can_process(data):
            return None
        value = str(data.get("Voice", "")).strip()
        if not value:
            return []
        if value.lower() in {"stop", "停止", "关闭"}:
            return ["stop voice"]
        return [f"play voice {value}"]
