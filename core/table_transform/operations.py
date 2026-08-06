"""Built-in table operations covering common workbook maintenance tasks."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Mapping, Tuple

import pandas as pd

from .base import OperationContext, TableOperation, find_column
from .conditions import matches_condition
from .models import CellChange, is_empty, values_equal


def _change(
    operation: TableOperation,
    context: OperationContext,
    row_index: int,
    column: str,
    new_value: Any,
    reason: str,
) -> CellChange:
    return CellChange(
        file=str(context.file_path),
        sheet=context.sheet_name,
        row=row_index + 2,
        dataframe_index=row_index,
        column=column,
        original_value=context.dataframe.at[row_index, column],
        new_value=new_value,
        operation=operation.id,
        reason=reason,
    )


class SetDefaultOperation(TableOperation):
    operation_type = "set_default"

    def plan(self, context: OperationContext) -> List[CellChange]:
        target = find_column(context.dataframe, self.config.get("target"), f"{self.id}.target")
        if target is None:
            return []
        value = self.config.get("value", self.options.get("value", ""))
        overwrite = bool(self.options.get("overwrite", False))
        changes = []
        for row_index, row in context.dataframe.iterrows():
            current = row[target]
            if (overwrite or is_empty(current)) and matches_condition(row, self.when):
                changes.append(_change(self, context, row_index, target, value, "default"))
        return changes


class CopyNearestOperation(TableOperation):
    operation_type = "copy_nearest"

    def plan(self, context: OperationContext) -> List[CellChange]:
        dataframe = context.dataframe
        target = find_column(dataframe, self.config.get("target"), f"{self.id}.target")
        if target is None:
            return []
        source = find_column(
            dataframe,
            self.config.get("source", self.config.get("target")),
            f"{self.id}.source",
        )
        if source is None:
            return []
        direction = self.options.get("direction", "upward")
        if direction not in ("upward", "downward"):
            raise ValueError(f"{self.id}.options.direction 必须是 upward 或 downward")
        overwrite = bool(self.options.get("overwrite", False))
        changes = []
        row_indexes = list(dataframe.index)
        positions = range(len(row_indexes)) if direction == "upward" else range(len(row_indexes) - 1, -1, -1)
        latest = None
        for position in positions:
            row_index = row_indexes[position]
            row = dataframe.loc[row_index]
            source_value = row[source]
            current = row[target]
            if not is_empty(source_value):
                latest = source_value
            if latest is None or not (overwrite or is_empty(current)):
                continue
            if matches_condition(row, self.when):
                changes.append(_change(self, context, row_index, target, latest, direction))
        return changes


class SequenceOperation(TableOperation):
    operation_type = "sequence"

    def plan(self, context: OperationContext) -> List[CellChange]:
        dataframe = context.dataframe
        target = find_column(dataframe, self.config.get("target"), f"{self.id}.target")
        if target is None:
            return []
        current_number = int(self.options.get("start", 1))
        step = int(self.options.get("step", 1))
        clear_invalid = bool(self.options.get("clear_invalid", False))
        changes = []
        for row_index, row in dataframe.iterrows():
            if matches_condition(row, self.when):
                value = current_number
                current_number += step
                if not values_equal(row[target], value):
                    changes.append(_change(self, context, row_index, target, value, "sequence"))
            elif clear_invalid and not is_empty(row[target]):
                changes.append(_change(self, context, row_index, target, "", "clear_invalid"))
        return changes


class TemplateOperation(TableOperation):
    operation_type = "template"

    def __init__(self, operation_id: str, config: Mapping[str, Any]):
        super().__init__(operation_id, config)
        self._counters: Dict[Tuple[Any, ...], int] = defaultdict(int)

    def reset(self) -> None:
        self._counters.clear()

    def _counter_key(
        self,
        context: OperationContext,
        variables: Mapping[str, Any],
    ) -> Tuple[Any, ...]:
        scope = self.options.get("counter_scope", "sheet")
        key: List[Any] = [self.id]
        if scope in ("file", "sheet"):
            key.append(str(context.file_path))
        if scope == "sheet":
            key.append(context.sheet_name)
        if scope not in ("global", "file", "sheet"):
            raise ValueError(f"{self.id}.options.counter_scope 必须是 global、file 或 sheet")
        counter_by = self.options.get("counter_by", [])
        if isinstance(counter_by, str):
            counter_by = [counter_by]
        if not isinstance(counter_by, list):
            raise ValueError(f"{self.id}.options.counter_by 必须是列名列表")
        key.extend(variables.get(column, "") for column in counter_by)
        return tuple(key)

    def plan(self, context: OperationContext) -> List[CellChange]:
        dataframe = context.dataframe
        target = find_column(dataframe, self.config.get("target"), f"{self.id}.target")
        if target is None:
            return []
        template = self.config.get("value", self.options.get("template"))
        if not isinstance(template, str):
            raise ValueError(f"{self.id}.value 必须是模板字符串")
        overwrite = bool(self.options.get("overwrite", False))
        start = int(self.options.get("start", 1))
        changes = []
        for row_index, row in dataframe.iterrows():
            if not (overwrite or is_empty(row[target])) or not matches_condition(row, self.when):
                continue
            variables = {
                key: "" if is_empty(value) else value for key, value in row.to_dict().items()
            }
            custom_variables = self.options.get("variables", {})
            if not isinstance(custom_variables, dict):
                raise ValueError(f"{self.id}.options.variables 必须是对象")
            for variable_name, column_aliases in custom_variables.items():
                column = find_column(dataframe, column_aliases, f"{self.id}.variables.{variable_name}")
                variables[str(variable_name)] = "" if column is None or is_empty(row[column]) else row[column]

            counter_key = self._counter_key(context, variables)
            self._counters[counter_key] += 1
            variables.update(
                {
                    "counter": start + self._counters[counter_key] - 1,
                    "row": row_index + 2,
                    "sheet": context.sheet_name,
                    "file": context.file_path.name,
                    "file_stem": context.file_path.stem,
                }
            )
            try:
                value = template.format_map(variables)
            except KeyError as exc:
                raise ValueError(f"{self.id}.value 引用了不存在的列或变量: {exc.args[0]}") from exc
            changes.append(_change(self, context, row_index, target, value, "template"))
        return changes


class MapValueOperation(TableOperation):
    operation_type = "map_value"

    def plan(self, context: OperationContext) -> List[CellChange]:
        dataframe = context.dataframe
        target = find_column(dataframe, self.config.get("target"), f"{self.id}.target")
        source = find_column(
            dataframe,
            self.config.get("source", self.config.get("target")),
            f"{self.id}.source",
        )
        if target is None or source is None:
            return []
        mapping = self.options.get("mapping", self.config.get("mapping"))
        if not isinstance(mapping, dict):
            raise ValueError(f"{self.id}.mapping 必须是对象")
        changes = []
        for row_index, row in dataframe.iterrows():
            source_value = row[source]
            if source_value in mapping and matches_condition(row, self.when):
                changes.append(
                    _change(self, context, row_index, target, mapping[source_value], "mapping")
                )
        return changes


class ClearWhenOperation(TableOperation):
    operation_type = "clear_when"

    def plan(self, context: OperationContext) -> List[CellChange]:
        target = find_column(context.dataframe, self.config.get("target"), f"{self.id}.target")
        if target is None:
            return []
        changes = []
        for row_index, row in context.dataframe.iterrows():
            if not is_empty(row[target]) and matches_condition(row, self.when):
                changes.append(_change(self, context, row_index, target, "", "condition"))
        return changes


class CopyColumnOperation(TableOperation):
    operation_type = "copy_column"

    def plan(self, context: OperationContext) -> List[CellChange]:
        dataframe = context.dataframe
        target = find_column(dataframe, self.config.get("target"), f"{self.id}.target")
        source = find_column(dataframe, self.config.get("source"), f"{self.id}.source")
        if target is None or source is None:
            return []
        overwrite = bool(self.options.get("overwrite", False))
        changes = []
        for row_index, row in dataframe.iterrows():
            if (overwrite or is_empty(row[target])) and not is_empty(row[source]) and matches_condition(row, self.when):
                changes.append(_change(self, context, row_index, target, row[source], "copy_column"))
        return changes


BUILTIN_OPERATIONS = (
    SetDefaultOperation,
    CopyNearestOperation,
    SequenceOperation,
    TemplateOperation,
    MapValueOperation,
    ClearWhenOperation,
    CopyColumnOperation,
)
