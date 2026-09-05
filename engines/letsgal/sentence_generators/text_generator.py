"""Generate LetsGal dialogue and narration code."""

from typing import Any, Dict, Optional

from engines.letsgal.generator_base import LetsGalGeneratorBase


class TextGenerator(LetsGalGeneratorBase):
    """Emit the code-layer dialogue form ``Name \"Text\"``."""

    param_config = {
        "Name": {},
        "Text": {},
        "Window": {},
    }

    @property
    def category(self) -> str:
        return "Text"

    @property
    def priority(self) -> int:
        return 900

    def can_process(self, data: Dict[str, Any]) -> bool:
        return not self.is_empty(data.get("Text"))

    def process(self, data: Dict[str, Any]) -> Optional[list[str]]:
        if not self.can_process(data):
            return None

        text = data.get("Text")
        name = data.get("Name")
        if not self.is_empty(name):
            name_text = str(name).strip()
            # Escape hatch for the small set of code-layer commands that do
            # not have a dedicated table column yet.
            if name_text.lower() in {"letsgal", "code"}:
                return [str(text)]
            return [f"{name_text} {self.quote_text(text)}"]
        return [self.quote_text(text)]
