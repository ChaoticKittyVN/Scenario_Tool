"""Export dynamic variant workbook data as an Agent-oriented JSON document."""

from __future__ import annotations

import json
import re
from string import Formatter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional

import pandas as pd

from core.logger import get_logger


logger = get_logger()

_EMPTY_GROUP = "_未分类"
_EMPTY_ITEM = "_无序号"
_ALIAS_SEPARATOR = re.compile(r"[,，、|;；]+")


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value == ""
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _json_value(value: Any) -> Any:
    if _is_empty(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if hasattr(value, "isoformat") and not isinstance(value, str):
        try:
            return value.isoformat()
        except (TypeError, ValueError):
            pass
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _text(value: Any) -> Optional[str]:
    value = _json_value(value)
    return None if value is None else str(value)


def _split_aliases(values: Iterable[Any]) -> List[str]:
    aliases: List[str] = []
    for value in values:
        text = _text(value)
        if text is None:
            continue
        for part in _ALIAS_SEPARATOR.split(text):
            alias = part.strip()
            if alias and alias not in aliases:
                aliases.append(alias)
    return aliases


def _append_index(index: MutableMapping[str, List[str]], key: str, record_id: str):
    record_ids = index.setdefault(key, [])
    if record_id not in record_ids:
        record_ids.append(record_id)


class VariantAgentExportMixin:
    """Build a canonical variant registry plus selection indexes for Agents."""

    def _variant_agent_output_file(self) -> Path:
        output_file = Path(self.config.variant_agent_export.output_file)
        if output_file.is_absolute():
            return output_file
        return Path(self.config.paths.param_config_dir) / output_file

    def _variant_sheet_profile(self, sheet_name: str) -> Dict[str, Any]:
        config = self.config.variant_agent_export
        profile: Dict[str, Any] = {
            "group_columns": list(config.group_columns),
            "item_key_column": config.item_key_column,
            "alias_columns": list(config.alias_columns),
            "parameter_template": config.parameter_template,
        }
        profiles = (
            config.sheet_profiles
            if isinstance(config.sheet_profiles, Mapping)
            else {}
        )
        wildcard = profiles.get("*", {})
        exact = profiles.get(sheet_name, {})
        if isinstance(wildcard, Mapping):
            profile.update(wildcard)
        if isinstance(exact, Mapping):
            profile.update(exact)
        for key in ("group_columns", "alias_columns"):
            value = profile.get(key) or []
            profile[key] = [value] if isinstance(value, str) else list(value)
        return profile

    def _compose_scenario_param(
        self,
        row_values: Mapping[str, Any],
        template: Optional[str],
    ) -> Optional[str]:
        existing = _text(row_values.get("ScenarioParam"))
        if existing is not None:
            return existing
        if not template:
            return None

        template_fields = {
            field_name
            for _, field_name, _, _ in Formatter().parse(template)
            if field_name
        }
        missing_columns = sorted(template_fields.difference(row_values))
        if missing_columns:
            raise ValueError(
                f"拼接模板引用了不存在的列: {', '.join(missing_columns)}"
            )
        empty_columns = sorted(
            field_name
            for field_name in template_fields
            if row_values.get(field_name) is None
        )
        if empty_columns:
            raise ValueError(
                f"拼接模板所需列为空: {', '.join(empty_columns)}"
            )

        format_values = {
            key: "" if value is None else value
            for key, value in row_values.items()
        }
        try:
            result = template.format_map(format_values)
        except KeyError as exc:
            raise ValueError(f"拼接模板引用了不存在的列: {exc.args[0]}") from exc
        return result if result != "" else None

    def _add_selection_index(
        self,
        groups: MutableMapping[str, Any],
        group_values: Iterable[str],
        item_key: str,
        record_id: str,
    ) -> None:
        branch = groups
        for group_value in group_values:
            branch = branch.setdefault(group_value, {})
        record_ids = branch.setdefault(item_key, [])
        record_ids.append(record_id)

    def _build_variant_sheet_document(
        self,
        sheet_name: str,
        dataframe: pd.DataFrame,
    ) -> Dict[str, Any]:
        profile = self._variant_sheet_profile(sheet_name)
        group_columns = profile["group_columns"]
        item_key_column = profile.get("item_key_column")
        alias_columns = profile["alias_columns"]
        parameter_template = profile.get("parameter_template")

        variants: Dict[str, Dict[str, Any]] = {}
        selection_groups: Dict[str, Any] = {}
        applicability_index: Dict[str, List[str]] = {}
        warnings: List[str] = []
        used_ids: Dict[str, int] = {}

        for row_number, (_, row) in enumerate(dataframe.iterrows(), start=2):
            row_values = {
                str(column): _json_value(value)
                for column, value in row.items()
            }
            if not any(value is not None for value in row_values.values()):
                continue

            excel_param = _text(row_values.get("ExcelParam"))
            try:
                scenario_param = self._compose_scenario_param(
                    row_values,
                    parameter_template,
                )
            except ValueError as exc:
                raise ValueError(f"工作表 {sheet_name} 第 {row_number} 行: {exc}") from exc

            base_id = scenario_param or excel_param or f"row_{row_number}"
            duplicate_count = used_ids.get(base_id, 0)
            used_ids[base_id] = duplicate_count + 1
            record_id = base_id if duplicate_count == 0 else f"{base_id}#{duplicate_count + 1}"
            if duplicate_count:
                warnings.append(
                    f"第 {row_number} 行与已有记录使用相同参数 {base_id!r}，"
                    f"文档中改用 ID {record_id!r}。"
                )
            if scenario_param is None:
                warnings.append(f"第 {row_number} 行无法确定 ScenarioParam。")

            group_values = [
                _text(row_values.get(column)) or _EMPTY_GROUP
                for column in group_columns
            ]
            item_key = (
                _text(row_values.get(item_key_column)) if item_key_column else None
            ) or _EMPTY_ITEM
            aliases = _split_aliases(row_values.get(column) for column in alias_columns)

            record = {
                "excel_param": excel_param,
                "scenario_param": scenario_param,
                "groups": dict(zip(group_columns, group_values)),
                "item_key": item_key,
                "applicable_groups": aliases,
                "attributes": {
                    key: value
                    for key, value in row_values.items()
                    if key not in {"ExcelParam", "ScenarioParam"}
                },
            }
            variants[record_id] = record
            self._add_selection_index(
                selection_groups,
                group_values,
                item_key,
                record_id,
            )

            if group_values:
                _append_index(applicability_index, group_values[0], record_id)
            for alias in aliases:
                _append_index(applicability_index, alias, record_id)

        return {
            "profile": {
                "group_columns": group_columns,
                "item_key_column": item_key_column,
                "alias_columns": alias_columns,
                "parameter_template": parameter_template,
            },
            "variants": variants,
            "selection_index": {
                "group_columns": group_columns,
                "item_key_column": item_key_column,
                "groups": selection_groups,
            },
            "applicability_index": applicability_index,
            "warnings": warnings,
        }

    def build_agent_variant_document(self) -> Dict[str, Any]:
        """Read all dynamic workbook columns and build the Agent document."""
        variant_file = self._variant_data_file()
        if not variant_file.exists():
            raise FileNotFoundError(f"差分参数文件不存在: {variant_file}")

        sheets = self.excel_manager.load_excel(variant_file)
        sheet_documents = {
            sheet_name: self._build_variant_sheet_document(sheet_name, dataframe)
            for sheet_name, dataframe in sheets.items()
            if "模板" not in sheet_name
        }
        return {
            "schema_version": 1,
            "source_file": str(variant_file),
            "sheets": sheet_documents,
        }

    def export_agent_variant_document(self, dry_run: bool = False) -> bool:
        """Export the Agent document without changing normal mapping behavior."""
        try:
            document = self.build_agent_variant_document()
            output_file = self._variant_agent_output_file()
            content = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
            action = "将生成" if dry_run else "生成"
            logger.info(f"{action} Agent 差分文档: {output_file}")
            if dry_run:
                return True

            output_file.parent.mkdir(parents=True, exist_ok=True)
            if output_file.exists() and output_file.read_text(encoding="utf-8") == content:
                logger.info("Agent 差分文档内容未变化，跳过保存")
                return True
            output_file.write_text(content, encoding="utf-8")
            total = sum(
                len(sheet["variants"])
                for sheet in document["sheets"].values()
            )
            logger.info(
                f"Agent 差分文档已生成: {len(document['sheets'])} 个工作表, "
                f"{total} 个差分"
            )
            return True
        except Exception as exc:
            logger.error(f"生成 Agent 差分文档失败: {exc}", exc_info=True)
            return False
