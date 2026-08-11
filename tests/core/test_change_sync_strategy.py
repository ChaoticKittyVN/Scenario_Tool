import pandas as pd

from core.param_filler.filling_strategy import ChangeSyncStrategy


def test_normalizes_exporter_locator_names_and_filename_extension():
    changes = pd.DataFrame(
        [{"Filename": "chapter.xlsx", "Sheet": "Scene", "Index": 10}]
    )

    normalized = ChangeSyncStrategy.normalize_changes_dataframe(
        changes,
        required_columns=ChangeSyncStrategy.REQUIRED_LOCATOR_COLUMNS,
    )

    assert normalized.loc[0, "ExcelFilename"] == "chapter"
    assert normalized.loc[0, "SheetName"] == "Scene"


def test_locates_by_index_value_and_uses_idx_only_as_validation():
    source = pd.DataFrame(
        [
            {"Index": "scenario-100", "Text": "A"},
            {"Index": "scenario-200", "Text": "B"},
        ]
    )

    matched = ChangeSyncStrategy.locate_record(
        source,
        {"Index": "scenario-200", "Idx": 3},
    )
    mismatched = ChangeSyncStrategy.locate_record(
        source,
        {"Index": "scenario-200", "Idx": 2},
    )

    assert matched.position == 1
    assert matched.status == "matched"
    assert mismatched.position is None
    assert mismatched.status == "idx_mismatch"


def test_rejects_missing_and_ambiguous_index_values():
    source = pd.DataFrame(
        [
            {"Index": 10},
            {"Index": 10},
        ]
    )

    missing = ChangeSyncStrategy.locate_record(source, {"Index": 99})
    ambiguous = ChangeSyncStrategy.locate_record(source, {"Index": 10})

    assert missing.status == "index_not_found"
    assert ambiguous.status == "index_ambiguous"


def test_strategy_filters_normalized_changes_by_workbook_and_sheet():
    strategy = ChangeSyncStrategy()
    strategy.set_changes_df(
        pd.DataFrame(
            [
                {"Filename": "chapter.xlsx", "Sheet": "Scene", "Index": 1, "Voice": "a"},
                {"Filename": "other.xlsx", "Sheet": "Scene", "Index": 2, "Voice": "b"},
            ]
        ),
        data_columns=["Voice"],
    )

    result = strategy.get_changes_for_sheet("chapter.xlsx", "Scene")

    assert result["Index"].tolist() == [1]
