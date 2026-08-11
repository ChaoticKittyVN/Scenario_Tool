from pathlib import Path

import pandas as pd
import pytest

from tools.sync_changes import ChangeSyncTool


def _configure_tool(changes: pd.DataFrame) -> ChangeSyncTool:
    tool = ChangeSyncTool(dry_run=True)
    tool.changes_df = tool._prepare_changes_dataframe(changes)
    strategy = tool.filler.strategy_manager.get("change_sync")
    strategy.set_changes_df(
        tool.changes_df,
        locator_columns=["ExcelFilename", "SheetName", "Index", "Idx"],
        data_columns=["Text"],
    )
    return tool


def test_review_and_legacy_text_records_can_be_processed_together():
    source = pd.DataFrame(
        [
            {"Index": 1, "Text": "original"},
            {"Index": 2, "Text": "rejected original"},
            {"Index": 3, "Text": "changed after review"},
            {"Index": 4, "Text": "legacy old"},
        ]
    )
    changes = pd.DataFrame(
        [
            {"ExcelFilename": "chapter", "SheetName": "Scene", "Index": 1, "Idx": 2,
             "OriginalText": "original", "ProposedText": "approved text", "Decision": "approve"},
            {"ExcelFilename": "chapter", "SheetName": "Scene", "Index": 2, "Idx": 3,
             "OriginalText": "rejected original", "ProposedText": "rejected text", "Decision": "reject"},
            {"ExcelFilename": "chapter", "SheetName": "Scene", "Index": 3, "Idx": 4,
             "OriginalText": "stale original", "ProposedText": "unsafe text", "Decision": "批准"},
            {"ExcelFilename": "chapter", "SheetName": "Scene", "Index": 4, "Idx": 5,
             "Text": "legacy new"},
        ]
    )
    tool = _configure_tool(changes)

    tool.process_dataframe(source, "Scene", Path("chapter.xlsx"))

    assert [(change.row, change.new_value) for change in tool.reporter.get_all_changes()] == [
        (2, "approved text"),
        (5, "legacy new"),
    ]


def test_review_contract_requires_all_review_columns():
    tool = ChangeSyncTool(dry_run=True)
    changes = pd.DataFrame(
        [{"ExcelFilename": "chapter", "SheetName": "Scene", "Index": 1,
          "OriginalText": "old", "ProposedText": "new"}]
    )

    with pytest.raises(ValueError, match="审核格式缺少必需列"):
        tool._prepare_changes_dataframe(changes)
