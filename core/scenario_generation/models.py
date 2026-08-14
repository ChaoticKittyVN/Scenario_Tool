"""Data models shared by production and range-test scenario generation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from core.excel_management import DataFrameProcessor
from core.param_process.param_translator import ParamTranslator


RANGE_MODE_TARGET_ONLY = "target-only"
RANGE_MODE_WARMUP = "warmup"
RANGE_MODE_CONTEXT = "context"
RANGE_MODE_PREFIX = "prefix"
RANGE_MODES = {
    RANGE_MODE_TARGET_ONLY,
    RANGE_MODE_WARMUP,
    RANGE_MODE_CONTEXT,
    RANGE_MODE_PREFIX,
}

_LABEL_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass
class GenerationSummary:
    total_files: int = 0
    succeeded_files: int = 0
    failed_files: int = 0
    untranslatable_count: int = 0
    untranslatable_log: Optional[Path] = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None and self.total_files > 0 and self.failed_files == 0


@dataclass
class GeneratedRowBlock:
    excel_row: int
    scenario_index: str
    command_count: int
    commands: list[Any] = field(repr=False)
    error: Optional[str] = None


@dataclass
class GenerationRuntime:
    translator: ParamTranslator
    processor: Any
    dataframe_processor: DataFrameProcessor


@dataclass(frozen=True)
class ScenarioRangeCase:
    """One requested test fragment using inclusive Excel row numbers."""

    sheet: str
    start_row: int
    end_row: int
    name: Optional[str] = None
    context_start: Optional[int] = None
    label: Optional[str] = None
    mode: str = RANGE_MODE_WARMUP
    replay_start: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.sheet.strip():
            raise ValueError("工作表名称不能为空")
        if self.start_row < 2:
            raise ValueError("起始行必须大于等于 2（Excel 第 1 行是表头）")
        if self.end_row < self.start_row:
            raise ValueError("结束行不能小于起始行")
        if self.mode not in RANGE_MODES:
            raise ValueError(f"不支持的范围执行模式: {self.mode}")
        if self.context_start is not None:
            if self.context_start < 2:
                raise ValueError("上下文起始行必须大于等于 2")
            if self.context_start > self.start_row:
                raise ValueError("上下文起始行不能晚于目标起始行")
        if self.mode == RANGE_MODE_CONTEXT and self.context_start is None:
            raise ValueError("context 模式必须指定 context_start")
        if (
            self.mode in {RANGE_MODE_TARGET_ONLY, RANGE_MODE_PREFIX}
            and self.context_start is not None
        ):
            raise ValueError(f"{self.mode} 模式不使用 context_start")
        if self.mode == RANGE_MODE_TARGET_ONLY and self.replay_start is not None:
            raise ValueError("target-only 模式不使用 replay_start")
        if self.replay_start is not None:
            if self.replay_start < 2:
                raise ValueError("状态回放起始行必须大于等于 2")
            if self.replay_start > self.output_start_row:
                raise ValueError("状态回放起始行不能晚于输出起始行")
        if self.label is not None and not _LABEL_PATTERN.fullmatch(self.label):
            raise ValueError(
                f"测试标签 {self.label!r} 无效；仅支持英文字母、数字和下划线，且不能以数字开头"
            )

    @property
    def effective_mode(self) -> str:
        # Preserve the original @CONTEXT_START shorthand.
        if self.mode == RANGE_MODE_WARMUP and self.context_start is not None:
            return RANGE_MODE_CONTEXT
        return self.mode

    @property
    def effective_replay_start(self) -> int:
        if self.effective_mode == RANGE_MODE_TARGET_ONLY:
            return self.start_row
        return self.replay_start if self.replay_start is not None else 2

    @property
    def output_start_row(self) -> int:
        if self.effective_mode == RANGE_MODE_CONTEXT:
            return self.context_start if self.context_start is not None else self.start_row
        if self.effective_mode == RANGE_MODE_PREFIX:
            return self.replay_start if self.replay_start is not None else 2
        return self.start_row

    @property
    def case_name(self) -> str:
        return self.name or f"{self.sheet}_R{self.start_row}-R{self.end_row}"


@dataclass
class ScenarioTestCaseResult:
    name: str
    sheet: str
    mode: str
    target_start: int
    target_end: int
    replay_start: int
    output_start: int
    label: Optional[str]
    output_file: Optional[str]
    processed_rows: int
    warmup_rows: int
    output_rows: int
    generated_commands: int
    skipped_rows: list[int]
    row_errors: dict[int, str]
    success: bool
