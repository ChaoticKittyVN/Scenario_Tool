from types import SimpleNamespace

import pandas as pd

from core.excel_management import DataFrameProcessor
from core.word_statistics import calculate_dataframe_word_statistics
from tools.count_words import build_report, discover_excel_files, filter_rows_by_name


def test_statistics_preserve_name_text_row_alignment():
    dataframe = pd.DataFrame(
        {
            "Name": ["Alice", "", "Bob", "Carol"],
            "Text": ["甲", "乙", "", "丙丁"],
        }
    )

    statistics = calculate_dataframe_word_statistics(dataframe)

    assert statistics.total == 4
    assert statistics.text_rows == 3
    assert statistics.by_speaker == {
        "Alice": 1,
        "unrecognized": 1,
        "Carol": 2,
    }
    assert statistics.speaker_total == statistics.total


def test_statistics_skip_missing_text_and_accept_missing_name_column():
    dataframe = pd.DataFrame({"Text": [None, "", "有效文本"]})

    statistics = calculate_dataframe_word_statistics(dataframe)

    assert statistics.total == 4
    assert statistics.text_rows == 1
    assert statistics.by_speaker == {"unrecognized": 4}


def test_word_count_report_uses_end_and_ignore_rules(tmp_path):
    workbook = tmp_path / "scenario.xlsx"
    dataframe = pd.DataFrame(
        {
            "Name": ["Alice", "Bob", "Carol", "", "Tail"],
            "Text": ["甲", "忽略文本", "乙", "", "不应统计"],
            "Note": ["", "", "", "END", ""],
            "Ignore": ["", "忽略", "", "", ""],
        }
    )
    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        dataframe.to_excel(writer, sheet_name="Scene", index=False)
        dataframe.to_excel(writer, sheet_name="参数表", index=False)

    config = SimpleNamespace(
        processing=SimpleNamespace(ignore_mode=True, ignore_words=["忽略"])
    )
    files = discover_excel_files([tmp_path])

    first_report = build_report(files, config)
    second_report = build_report(files, config)

    assert first_report == second_report
    assert first_report["total"] == 2
    assert first_report["text_rows"] == 2
    assert first_report["files"][0]["sheets"] == [
        {
            "name": "Scene",
            "total": 2,
            "text_rows": 2,
            "by_speaker": {"Alice": 1, "Carol": 1},
        }
    ]


def test_all_rows_mode_exposes_content_outside_generation_range(tmp_path):
    workbook = tmp_path / "scenario.xlsx"
    dataframe = pd.DataFrame(
        {
            "Name": ["Alice", "", "Tail"],
            "Text": ["甲", "", "乙"],
            "Note": ["", "END", ""],
        }
    )
    dataframe.to_excel(workbook, sheet_name="Scene", index=False)
    config = SimpleNamespace(
        processing=SimpleNamespace(ignore_mode=False, ignore_words=[])
    )

    report = build_report([workbook], config, all_rows=True)

    assert report["total"] == 2
    assert report["files"][0]["sheets"][0]["by_speaker"] == {
        "Alice": 1,
        "Tail": 1,
    }


def test_name_filters_exclude_special_names_by_default():
    dataframe = pd.DataFrame(
        {
            "Name": ["Alice", "Bob", "renpy", "label", "text", ""],
            "Text": ["甲", "乙", "命令", "标签", "旁白", "未知"],
        }
    )

    filtered = filter_rows_by_name(dataframe)

    assert filtered["Name"].tolist() == ["Alice", "Bob", ""]


def test_name_filters_support_only_exclude_and_selected_special_names():
    dataframe = pd.DataFrame(
        {
            "Name": ["Alice", "Bob", "Carol", "renpy", "label"],
            "Text": ["甲", "乙", "丙", "命令", "标签"],
        }
    )

    filtered = filter_rows_by_name(
        dataframe,
        only_names={"Alice", "Bob"},
        exclude_names={"Bob"},
        include_special_names={"label"},
    )

    assert filtered["Name"].tolist() == ["Alice", "label"]


def test_report_filters_selected_sheet_and_names(tmp_path):
    workbook = tmp_path / "scenario.xlsx"
    scene_a = pd.DataFrame(
        {
            "Name": ["Alice", "Bob", "label", ""],
            "Text": ["甲", "乙", "标签", ""],
            "Note": ["", "", "", "END"],
        }
    )
    scene_b = pd.DataFrame(
        {
            "Name": ["Alice", ""],
            "Text": ["不应统计", ""],
            "Note": ["", "END"],
        }
    )
    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        scene_a.to_excel(writer, sheet_name="SceneA", index=False)
        scene_b.to_excel(writer, sheet_name="SceneB", index=False)
    config = SimpleNamespace(
        processing=SimpleNamespace(ignore_mode=False, ignore_words=[])
    )

    report = build_report(
        [workbook],
        config,
        sheets=["SceneA"],
        only_names=["Alice"],
        include_special_names=["label"],
    )

    assert report["total"] == 3
    assert report["files"][0]["sheets"][0]["by_speaker"] == {
        "Alice": 1,
        "label": 2,
    }
