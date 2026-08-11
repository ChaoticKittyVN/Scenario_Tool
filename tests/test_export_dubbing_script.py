from types import SimpleNamespace

import pandas as pd
import pytest

from tools.export_dubbing_script import (
    DialogueExporter,
    VOICE_MODE_AUTO_PRESET,
    VOICE_MODE_CAPTURE,
)


def _make_exporter(tmp_path, voice_mode=VOICE_MODE_CAPTURE):
    config = SimpleNamespace(
        paths=SimpleNamespace(input_dir=tmp_path, output_dir=tmp_path),
    )
    exporter = DialogueExporter(config=config, voice_mode=voice_mode)
    exporter.df_processor.extract_valid_rows = lambda df, sheet_name: df
    return exporter


def _source_dataframe():
    return pd.DataFrame(
        [
            {"Name": "主角", "Text": "第一句", "Voice": "recorded/line_01.wav", "Index": 10},
            {"Name": "主角", "Text": "第二句", "Voice": pd.NA, "Index": 11},
        ]
    )


def test_capture_mode_is_default_and_uses_source_voice_values(tmp_path, monkeypatch):
    exporter = _make_exporter(tmp_path)
    monkeypatch.setattr(
        exporter.excel_manager,
        "load_excel",
        lambda file_path: {"Scene01": _source_dataframe()},
    )

    result = exporter.extract_from_file(tmp_path / "chapter.xlsx")

    assert exporter.voice_mode == VOICE_MODE_CAPTURE
    assert exporter.sort_by == ["Name", "Idx"]
    assert result["Voice"].tolist() == ["recorded/line_01.wav", ""]


def test_auto_preset_mode_keeps_existing_generated_voice_names(tmp_path, monkeypatch):
    exporter = _make_exporter(tmp_path, voice_mode=VOICE_MODE_AUTO_PRESET)
    monkeypatch.setattr(
        exporter.excel_manager,
        "load_excel",
        lambda file_path: {"Scene01": _source_dataframe()},
    )

    result = exporter.extract_from_file(tmp_path / "chapter.xlsx")

    assert result["Voice"].tolist() == ["hero_Scene01_001", "hero_Scene01_002"]


def test_rejects_unknown_voice_mode(tmp_path):
    with pytest.raises(ValueError, match="不支持的 Voice 输出模式"):
        _make_exporter(tmp_path, voice_mode="unknown")


def test_filters_and_name_to_voice_aliases_share_numbering(tmp_path, monkeypatch):
    config = SimpleNamespace(
        paths=SimpleNamespace(input_dir=tmp_path, output_dir=tmp_path),
    )
    exporter = DialogueExporter(
        config=config,
        voice_mode=VOICE_MODE_AUTO_PRESET,
        selected_characters=["爱丽丝", "神秘少女"],
        selected_sheets=["Scene01"],
        sync_ready=True,
    )
    exporter.df_processor.extract_valid_rows = lambda df, sheet_name: df
    monkeypatch.setattr(
        exporter.translator,
        "get_mapping",
        lambda mapping_type, name: {
            "爱丽丝": "alice",
            "神秘少女": "alice",
        }.get(name),
    )
    monkeypatch.setattr(
        exporter.excel_manager,
        "load_excel",
        lambda file_path: {
            "Scene01": pd.DataFrame(
                [
                    {"Name": "爱丽丝", "Text": "第一句", "Index": 1},
                    {"Name": "神秘少女", "Text": "第二句", "Index": 2},
                    {"Name": "其他角色", "Text": "不导出", "Index": 3},
                ]
            ),
            "Scene02": pd.DataFrame(
                [{"Name": "爱丽丝", "Text": "不导出", "Index": 4}]
            ),
        },
    )

    result = exporter.extract_from_file(tmp_path / "chapter.xlsx")

    assert result.columns.tolist()[:2] == ["ExcelFilename", "SheetName"]
    assert result["Name"].tolist() == ["爱丽丝", "神秘少女"]
    assert result["Voice"].tolist() == [
        "alice_Scene01_001",
        "alice_Scene01_002",
    ]
