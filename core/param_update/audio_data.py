"""Resolve and validate the authoritative, project-scoped audio data source."""

from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Dict, List, Optional

from openpyxl import load_workbook

from core.logger import get_logger

AUDIO_TYPES = ("Music", "Ambience", "Sound")
logger = get_logger()


def _empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _json_cell(value: Any) -> Any:
    if _empty(value):
        return None
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    return value


@dataclass
class AudioSource:
    """One source workbook, with records keyed by type and ExcelParam."""

    path: Path
    project: Optional[str]
    sheets: Dict[str, Dict[str, Dict[str, Any]]]
    source_files: List[Path] = field(default_factory=list)

    def mappings(self) -> Dict[str, Dict[str, str]]:
        return {
            audio_type: {
                excel_param: record["scenario_param"]
                for excel_param, record in records.items()
            }
            for audio_type, records in self.sheets.items()
        }


def read_audio_source(path: Path, project: Optional[str] = None) -> AudioSource:
    """Read audio mappings and preserve optional descriptions as ordinary cells."""
    workbook = load_workbook(path, read_only=True, data_only=True)
    sheets = {}
    try:
        for sheet in workbook:
            if sheet.title not in AUDIO_TYPES:
                continue
            rows = sheet.iter_rows()
            headers = [cell.value for cell in next(rows, ())]
            while headers and _empty(headers[-1]):
                headers.pop()
            location = f"{path.name}/{sheet.title}"
            if any(
                not isinstance(header, str)
                or not header.strip()
                for header in headers
            ):
                raise ValueError(f"{location}: 列名必须是非空文本")
            if len(headers) != len(set(headers)):
                raise ValueError(f"{location}: 存在重复列名")
            missing = {"ExcelParam", "ScenarioParam"}.difference(headers)
            if missing:
                raise ValueError(f"{location}: 缺少必需列 {', '.join(sorted(missing))}")
            records = {}
            for row_number, cells in enumerate(rows, start=2):
                if all(_empty(cell.value) for cell in cells):
                    continue
                row_location = f"{location} 第 {row_number} 行"
                if any(cell.data_type == "e" for cell in cells):
                    raise ValueError(f"{row_location}: 不接受 Excel 错误值")
                if any(not _empty(cell.value) for cell in cells[len(headers) :]):
                    raise ValueError(f"{row_location}: 存在没有列名的数据")
                values = {
                    header: _json_cell(cell.value)
                    for header, cell in zip(headers, cells)
                }
                for column in ("ExcelParam", "ScenarioParam"):
                    value = values.get(column)
                    if _empty(value):
                        raise ValueError(f"{row_location}: {column} 必须是非空参数值")
                    values[column] = str(value)
                excel_param = values["ExcelParam"]
                if excel_param in records:
                    raise ValueError(f"{row_location}: 重复 ExcelParam {excel_param!r}")
                records[excel_param] = {
                    "excel_param": excel_param,
                    "scenario_param": values["ScenarioParam"],
                    "source_file": str(path),
                    "source_row": row_number,
                    "attributes": {
                        key: value
                        for key, value in values.items()
                        if key not in {"ExcelParam", "ScenarioParam"}
                    },
                }
            sheets[sheet.title] = records
        if not sheets:
            raise ValueError(f"{path.name}: 缺少 Music、Ambience 或 Sound 工作表")
        return AudioSource(path, project, sheets, [path])
    finally:
        workbook.close()


class AudioDataMixin:
    """Use one validated source for mappings, candidates and audio documents."""

    @property
    def audio_data_enabled(self) -> bool:
        settings = getattr(self.config, "audio_data", None)
        return getattr(settings, "enabled", False) is True

    def _audio_data_file(self, project: Optional[str] = None) -> Path:
        param_dir = Path(self.config.paths.param_config_dir)
        candidates = [param_dir / "audio_data.xlsx"]
        if project is not None:
            candidates.insert(0, param_dir / f"audio_data_{project}.xlsx")
        for candidate in candidates:
            if candidate.exists():
                return candidate
        raise FileNotFoundError(
            "已启用 audio_data，但音频资料文件不存在: "
            + " 或 ".join(str(candidate) for candidate in candidates)
        )

    def _audio_source_for_project(
        self,
        sources: Dict[Optional[str], AudioSource],
        project: Optional[str],
    ) -> Optional[AudioSource]:
        if not self.multi_project_mode or not self.projects:
            return next(iter(sources.values()), None)
        keys = (None,) if project is None else (None, project)
        selected = [sources[key] for key in keys if key in sources]
        if not selected:
            return None
        sheets = self._merge_mappings([source.sheets for source in selected])
        merged = self._merge_mappings([source.sheets for source in sources.values()])
        for audio_type, records in sheets.items():
            for alias, record in records.items():
                winner = merged[audio_type][alias]
                if record["scenario_param"] != winner["scenario_param"]:
                    logger.warning(
                        f"音频映射 {audio_type}/{alias} 沿用普通参数的全局覆盖规则: "
                        f"{record['source_file']} -> {record['scenario_param']!r} "
                        f"被 {winner['source_file']} -> {winner['scenario_param']!r} 覆盖"
                    )
                    records[alias] = winner
        source_files = {str(source.path) for source in selected}
        source_files.update(
            record["source_file"]
            for records in sheets.values()
            for record in records.values()
        )
        return AudioSource(
            selected[-1].path,
            project,
            sheets,
            [source.path for source in sources.values() if str(source.path) in source_files],
        )

    def _effective_audio_sources(
        self, sources: Dict[Optional[str], AudioSource]
    ) -> Dict[Optional[str], AudioSource]:
        if not self.multi_project_mode or not self.projects:
            return sources
        common = self._audio_source_for_project(sources, None)
        effective = {None: common} if common is not None else {}
        for project in self.projects:
            source = self._audio_source_for_project(sources, project)
            if source is not None:
                effective[project] = source
        return effective

    def _load_audio_sources(self) -> Dict[Optional[str], AudioSource]:
        if not self.audio_data_enabled:
            return {}
        if len(self.projects) > 1 and not self.multi_project_mode:
            raise ValueError(
                "启用 audio_data 时，多个 projects 必须使用 multi_project_mode"
            )
        if self.multi_project_mode and self.projects:
            param_dir = Path(self.config.paths.param_config_dir)
            common_file = param_dir / "audio_data.xlsx"
            sources = {}
            if common_file.exists():
                sources[None] = read_audio_source(common_file)
            for project in self.projects:
                project_file = param_dir / f"audio_data_{project}.xlsx"
                if project_file.exists():
                    sources[project] = read_audio_source(project_file, project)
                elif None not in sources:
                    self._audio_data_file(project)
        else:
            project = next(iter(self.projects), None)
            sources = {
                project: read_audio_source(self._audio_data_file(project), project)
            }
        owned_types = {
            audio_type for source in sources.values() for audio_type in source.sheets
        }
        param_files = [self._default_param_file()]
        param_files.extend(path for path, _ in self._find_project_param_files())
        for param_file in dict.fromkeys(param_files):
            if not param_file.exists():
                continue
            for sheet_name, dataframe in self.excel_manager.load_excel(
                param_file
            ).items():
                if sheet_name in owned_types and any(
                    not _empty(value)
                    for row in dataframe.itertuples(index=False, name=None)
                    for value in row
                ):
                    raise ValueError(
                        f"{param_file.name}/{sheet_name}: audio_data 已接管该类型，"
                        "param_data 不得保留同类型数据；请人工迁出旧数据，不能合并或覆盖"
                    )
        return sources

    def _with_audio_mappings(
        self, mappings: Dict[str, Dict[str, str]]
    ) -> Dict[str, Dict[str, str]]:
        sources = self._load_audio_sources()
        if not sources:
            return mappings
        result = {key: dict(value) for key, value in mappings.items()}
        for source in sources.values():
            for audio_type in source.sheets:
                result[audio_type] = {}
        return self._merge_mappings(
            [result] + [source.mappings() for source in sources.values()]
        )

    def _with_audio_validation(
        self,
        validation_data: Dict[str, List[str]],
        project: Optional[str] = None,
    ) -> Dict[str, List[str]]:
        sources = self._load_audio_sources()
        if not sources:
            return validation_data
        owned_types = {
            audio_type for source in sources.values() for audio_type in source.sheets
        }
        result = {
            key: values
            for key, values in validation_data.items()
            if key not in owned_types
        }
        source = self._audio_source_for_project(sources, project)
        if source is None:
            return result
        return self._merge_validation_data(
            [
                result,
                {
                    audio_type: list(records)
                    for audio_type, records in source.sheets.items()
                },
            ]
        )
