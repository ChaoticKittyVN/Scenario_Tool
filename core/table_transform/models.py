"""Data models shared by table transformation engines and frontends."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


def is_empty(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return isinstance(value, str) and value == ""


def values_equal(left: Any, right: Any) -> bool:
    if is_empty(left) and is_empty(right):
        return True
    try:
        result = left == right
        return bool(result) if not pd.isna(result) else False
    except (TypeError, ValueError):
        return False


def json_value(value: Any) -> Any:
    if is_empty(value):
        return "" if isinstance(value, str) else None
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    return value


@dataclass
class CellChange:
    file: str
    sheet: str
    row: int
    dataframe_index: int
    column: str
    original_value: Any
    new_value: Any
    operation: str
    reason: str = ""

    @property
    def key(self) -> Tuple[str, int, str]:
        return self.sheet, self.row, self.column

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["original_value"] = json_value(self.original_value)
        data["new_value"] = json_value(self.new_value)
        return data


@dataclass
class ChangeConflict:
    key: Tuple[str, int, str]
    existing_operation: str
    incoming_operation: str


@dataclass
class ChangePlan:
    file_path: Path
    changes: List[CellChange] = field(default_factory=list)
    conflicts: List[ChangeConflict] = field(default_factory=list)
    sheets_processed: int = 0
    _positions: Dict[Tuple[str, int, str], int] = field(default_factory=dict, repr=False)

    def add(self, change: CellChange, conflict_policy: str = "error") -> bool:
        if values_equal(change.original_value, change.new_value):
            return False
        position = self._positions.get(change.key)
        if position is None:
            self._positions[change.key] = len(self.changes)
            self.changes.append(change)
            return True

        existing = self.changes[position]
        self.conflicts.append(
            ChangeConflict(change.key, existing.operation, change.operation)
        )
        if conflict_policy == "first":
            return False
        if conflict_policy == "last":
            change.original_value = existing.original_value
            self.changes[position] = change
            return True
        raise ValueError(
            f"单元格 {change.sheet}!{change.column}{change.row} 同时被 "
            f"{existing.operation} 和 {change.operation} 修改"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": str(self.file_path),
            "sheets_processed": self.sheets_processed,
            "change_count": len(self.changes),
            "conflicts": [asdict(conflict) for conflict in self.conflicts],
            "changes": [change.to_dict() for change in self.changes],
        }


@dataclass
class FileTransformResult:
    file_path: Path
    success: bool
    applied: bool
    plan: ChangePlan
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": str(self.file_path),
            "success": self.success,
            "applied": self.applied,
            "error": self.error,
            "plan": self.plan.to_dict(),
        }
