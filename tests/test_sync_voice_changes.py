from pathlib import Path

import pandas as pd

from tools.sync_voice_changes import ChangeSyncTool


def _configure_tool(changes: pd.DataFrame) -> ChangeSyncTool:
    tool = ChangeSyncTool(dry_run=True)
    tool.changes_df = tool._prepare_changes_dataframe(changes)
    strategy = tool.filler.strategy_manager.get("change_sync")
    strategy.set_changes_df(
        tool.changes_df,
        locator_columns=["ExcelFilename", "SheetName", "Index", "Idx", "Text", "Name"],
        data_columns=["Voice"],
    )
    return tool


def test_voice_sync_uses_index_and_reports_cross_check_results():
    source = pd.DataFrame(
        [
            {"Index": 100, "Idx": "source-only", "Name": "Alice", "Text": "A", "Voice": "old-a"},
            {"Index": 101, "Name": "Bob", "Text": "B", "Voice": "old-b"},
            {"Index": 102, "Name": "Carol", "Text": "C", "Voice": "same"},
        ]
    )
    changes = pd.DataFrame(
        [
            {"Filename": "chapter.xlsx", "Sheet": "Scene", "Index": 100, "Idx": 2,
             "Name": "Alice", "Text": "A", "Voice": "new-a"},
            {"Filename": "chapter", "Sheet": "Scene", "Index": 101, "Idx": 3,
             "Name": "Bob", "Text": "wrong", "Voice": "new-b"},
            {"Filename": "chapter", "Sheet": "Scene", "Index": 999, "Idx": 4,
             "Name": "Nobody", "Text": "missing", "Voice": "new-missing"},
            {"Filename": "chapter", "Sheet": "Scene", "Index": 102, "Idx": 4,
             "Name": "Carol", "Text": "C", "Voice": "same"},
        ]
    )
    tool = _configure_tool(changes)

    tool.process_dataframe(source, "Scene", Path("chapter.xlsx"))

    pending = tool.reporter.get_all_changes()
    assert [(change.row, change.column, change.new_value) for change in pending] == [
        (2, "Voice", "new-a")
    ]
    assert tool.get_sync_summary(finalize=True) == {
        "matched": 2,
        "conflicts": 1,
        "skipped": 1,
        "pending_changes": 1,
    }


def test_voice_sync_rejects_idx_that_disagrees_with_index():
    source = pd.DataFrame(
        [{"Index": 10, "Name": "Alice", "Text": "A", "Voice": "old"}]
    )
    changes = pd.DataFrame(
        [{"ExcelFilename": "chapter", "SheetName": "Scene", "Index": 10,
          "Idx": 99, "Voice": "new"}]
    )
    tool = _configure_tool(changes)

    tool.process_dataframe(source, "Scene", Path("chapter.xlsx"))

    assert tool.reporter.get_all_changes() == []
    assert tool.get_sync_summary(finalize=True)["conflicts"] == 1
