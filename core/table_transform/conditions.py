"""Declarative row-condition evaluation for table operations."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from .models import is_empty, values_equal


def _columns(value: Any) -> Sequence[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable) and not isinstance(value, Mapping):
        return [str(item) for item in value]
    raise ValueError(f"列条件必须是列名或列名列表: {value!r}")


def _value(row: pd.Series, column: str) -> Any:
    return row[column] if column in row.index else None


def _existing_values(row: pd.Series, columns: Sequence[str]) -> list[Any]:
    return [row[column] for column in columns if column in row.index]


def matches_condition(row: pd.Series, condition: Any) -> bool:
    if condition in (None, {}, []):
        return True
    if not isinstance(condition, Mapping):
        raise ValueError("when 必须是对象。")

    if "all" in condition:
        clauses = condition["all"]
        if not isinstance(clauses, list):
            raise ValueError("when.all 必须是列表。")
        if not all(matches_condition(row, clause) for clause in clauses):
            return False
    if "any" in condition:
        clauses = condition["any"]
        if not isinstance(clauses, list):
            raise ValueError("when.any 必须是列表。")
        if not any(matches_condition(row, clause) for clause in clauses):
            return False

    if "empty" in condition:
        columns = _columns(condition["empty"])
        values = _existing_values(row, columns)
        if len(values) != len(columns) or not all(is_empty(value) for value in values):
            return False
    if "nonempty" in condition:
        columns = _columns(condition["nonempty"])
        values = _existing_values(row, columns)
        if len(values) != len(columns) or not all(not is_empty(value) for value in values):
            return False
    if "empty_any" in condition:
        values = _existing_values(row, _columns(condition["empty_any"]))
        if not values or not any(is_empty(value) for value in values):
            return False
    if "nonempty_any" in condition:
        values = _existing_values(row, _columns(condition["nonempty_any"]))
        if not values or not any(not is_empty(value) for value in values):
            return False

    for key, expected_match in (("equals", True), ("not_equals", False)):
        values = condition.get(key)
        if values is None:
            continue
        if not isinstance(values, Mapping):
            raise ValueError(f"when.{key} 必须是对象。")
        for column, expected in values.items():
            if str(column) not in row.index:
                return False
            if values_equal(_value(row, str(column)), expected) != expected_match:
                return False

    for key, expected_match in (("in", True), ("not_in", False)):
        values = condition.get(key)
        if values is None:
            continue
        if not isinstance(values, Mapping):
            raise ValueError(f"when.{key} 必须是对象。")
        for column, choices in values.items():
            if str(column) not in row.index:
                return False
            if not isinstance(choices, list):
                raise ValueError(f"when.{key}.{column} 必须是列表。")
            contains = any(values_equal(_value(row, str(column)), choice) for choice in choices)
            if contains != expected_match:
                return False

    known_keys = {
        "all", "any", "empty", "nonempty", "empty_any", "nonempty_any",
        "equals", "not_equals", "in", "not_in",
    }
    unknown = set(condition) - known_keys
    if unknown:
        raise ValueError(f"不支持的条件字段: {', '.join(sorted(unknown))}")
    return True
