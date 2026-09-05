"""Formatter for LetsGal Studio's Ren'Py-style code view."""

from typing import Any, List

from core.scenario_output.base import IFormatter


class LetsgalFormatter(IFormatter):
    """Keep generated code lines intact and avoid Ren'Py indentation."""

    def format(self, structured_data: dict) -> Any:
        return structured_data

    def format_output(self, data: Any, engine_config: Any) -> List[str]:
        if not isinstance(data, list):
            return []
        return [line if isinstance(line, str) else str(line) for line in data]

    def get_format_type(self) -> str:
        return "text"

    def get_engine_type(self) -> str:
        return "letsgal"
