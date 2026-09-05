"""Generate comments for LetsGal code output."""

from typing import Any, Dict, Optional

from engines.letsgal.generator_base import LetsGalGeneratorBase


class NoteGenerator(LetsGalGeneratorBase):
    param_config = {"Note": {}}

    @property
    def category(self) -> str:
        return "Note"

    @property
    def priority(self) -> int:
        return 0

    def process(self, data: Dict[str, Any]) -> Optional[list[str]]:
        if not self.can_process(data):
            return None
        note = data.get("Note")
        return [f"# {note}"] if not self.is_empty(note) else []
