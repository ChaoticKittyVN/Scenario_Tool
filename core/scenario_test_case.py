"""Backward-compatible imports for scenario range-test generation."""

from core.scenario_generation import (
    RANGE_MODES,
    RANGE_MODE_CONTEXT,
    RANGE_MODE_PREFIX,
    RANGE_MODE_TARGET_ONLY,
    RANGE_MODE_WARMUP,
    ScenarioRangeCase,
    ScenarioTestCaseGenerator,
    ScenarioTestCaseResult,
)


__all__ = [
    "RANGE_MODES",
    "RANGE_MODE_CONTEXT",
    "RANGE_MODE_PREFIX",
    "RANGE_MODE_TARGET_ONLY",
    "RANGE_MODE_WARMUP",
    "ScenarioRangeCase",
    "ScenarioTestCaseGenerator",
    "ScenarioTestCaseResult",
]
