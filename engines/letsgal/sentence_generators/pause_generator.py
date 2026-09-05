"""Generate LetsGal wait code."""

from typing import Any, Dict, Optional

from engines.letsgal.generator_base import LetsGalGeneratorBase


class PauseGenerator(LetsGalGeneratorBase):
    """Convert the shared Pause cell to ``pause`` code."""

    param_config = {"Pause": {}}

    @property
    def category(self) -> str:
        return "Pause"

    @property
    def priority(self) -> int:
        return 500

    def process(self, data: Dict[str, Any]) -> Optional[list[str]]:
        if not self.can_process(data):
            return None
        value = str(data.get("Pause", "")).strip()
        if not value:
            return []
        if value.lower() in {"hard", "input", "click", "点击", "等待点击"}:
            return ["pause"]
        if value.endswith("ms"):
            self.normalize_number(value[:-2], field="Pause")
            return [f"pause {value}"]
        return [f"pause {self.normalize_number(value, field='Pause')}"]
