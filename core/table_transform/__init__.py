"""Reusable table transformation planning and execution."""

from .base import OperationContext, TableOperation
from .engine import (
    TableTransformEngine,
    TransformDefinition,
    load_definition,
    summarize_results,
)
from .models import CellChange, ChangePlan, FileTransformResult
from .registry import OperationRegistry

__all__ = [
    "CellChange",
    "ChangePlan",
    "FileTransformResult",
    "OperationContext",
    "OperationRegistry",
    "TableOperation",
    "TableTransformEngine",
    "TransformDefinition",
    "load_definition",
    "summarize_results",
]
