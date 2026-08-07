"""Stable, row-aligned word statistics for scenario tables."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import pandas as pd

from core.constants import ColumnName
from core.word_counter import BasicWordCounter


UNRECOGNIZED_SPEAKER = "unrecognized"


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


@dataclass(frozen=True)
class WordStatistics:
    """Statistics for one table while preserving row alignment."""

    total: int = 0
    text_rows: int = 0
    by_speaker: Dict[str, int] = field(default_factory=dict)

    @property
    def speaker_total(self) -> int:
        return sum(self.by_speaker.values())


def calculate_dataframe_word_statistics(
    df: pd.DataFrame,
    counter: Optional[BasicWordCounter] = None,
    name_column: str = ColumnName.NAME.value,
    text_column: str = ColumnName.TEXT.value,
) -> WordStatistics:
    """Count a DataFrame without independently filtering paired columns."""
    if text_column not in df.columns:
        return WordStatistics()

    counter = counter or BasicWordCounter()
    total = 0
    text_rows = 0
    by_speaker: Dict[str, int] = {}

    has_name_column = name_column in df.columns
    for _, row in df.iterrows():
        text = row[text_column]
        if _is_missing(text) or str(text).strip() == "":
            continue

        line_count = counter.count([text])
        total += line_count
        text_rows += 1

        speaker_value = row[name_column] if has_name_column else None
        if _is_missing(speaker_value) or str(speaker_value).strip() == "":
            speaker = UNRECOGNIZED_SPEAKER
        else:
            speaker = str(speaker_value).strip()
        by_speaker[speaker] = by_speaker.get(speaker, 0) + line_count

    return WordStatistics(total=total, text_rows=text_rows, by_speaker=by_speaker)
