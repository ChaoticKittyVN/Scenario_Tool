"""Extension interfaces for reusable and project-specific table operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import pandas as pd

from .models import CellChange


@dataclass
class OperationContext:
    file_path: Path
    sheet_name: str
    dataframe: pd.DataFrame


class TableOperation(ABC):
    """Plan table changes without writing a workbook."""

    operation_type = "custom"

    def __init__(self, operation_id: str, config: Mapping[str, Any]):
        self.id = operation_id
        self.config = dict(config)
        self.when = self.config.get("when", {})
        self.options: Dict[str, Any] = dict(self.config.get("options", {}))

    def reset(self) -> None:
        """Reset state before a new directory run."""

    @abstractmethod
    def plan(self, context: OperationContext) -> List[CellChange]:
        """Return proposed changes for one worksheet."""


def aliases(value: Any, label: str) -> Sequence[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and value and all(isinstance(item, str) for item in value):
        return value
    raise ValueError(f"{label} 必须是列名或非空列名列表。")


def resolve_column(dataframe: pd.DataFrame, value: Any, label: str) -> str:
    candidates = aliases(value, label)
    for candidate in candidates:
        if candidate in dataframe.columns:
            return candidate
    raise ValueError(f"{label} 未匹配工作表列: {', '.join(candidates)}")


def find_column(dataframe: pd.DataFrame, value: Any, label: str) -> str | None:
    candidates = aliases(value, label)
    return next((candidate for candidate in candidates if candidate in dataframe.columns), None)
