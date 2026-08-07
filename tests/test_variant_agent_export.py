import json

import pandas as pd

from core.config_manager import AppConfig
from core.param_update import ParamUpdater
from engines.renpy.config import RenpyConfig


def _updater(tmp_path):
    config = AppConfig(engine=RenpyConfig())
    config.paths.param_config_dir = tmp_path / "param_config"
    config.paths.param_config_dir.mkdir()
    return ParamUpdater(config)


def test_agent_variant_export_preserves_dynamic_columns_and_builds_indexes(tmp_path):
    updater = _updater(tmp_path)
    variant_file = updater.config.paths.param_config_dir / "variant_data.xlsx"
    with pd.ExcelWriter(variant_file, engine="openpyxl") as writer:
        pd.DataFrame(
            {
                "ExcelParam": ["微笑一", "认真二"],
                "ScenarioParam": [None, "angry2"],
                "情绪": ["smile", "angry"],
                "序号": [1, 2],
                "适用情绪": ["温柔，安心", "认真|担忧"],
                "眼睛": ["半闭眼", "凝视"],
                "嘴": ["轻微微笑", "闭合"],
            }
        ).to_excel(writer, sheet_name="角色A", index=False)

    assert updater.export_agent_variant_document() is True

    output_file = updater.config.paths.param_config_dir / "variant_agent_data.json"
    document = json.loads(output_file.read_text(encoding="utf-8"))
    role = document["sheets"]["角色A"]
    smile = role["variants"]["smile1"]

    assert smile["scenario_param"] == "smile1"
    assert smile["attributes"]["眼睛"] == "半闭眼"
    assert role["selection_index"]["groups"]["smile"]["1"] == ["smile1"]
    assert role["applicability_index"]["温柔"] == ["smile1"]
    assert role["applicability_index"]["安心"] == ["smile1"]
    assert role["applicability_index"]["认真"] == ["angry2"]


def test_agent_variant_export_supports_per_sheet_column_profiles(tmp_path):
    updater = _updater(tmp_path)
    updater.config.variant_agent_export.sheet_profiles = {
        "角色B": {
            "group_columns": ["分类"],
            "item_key_column": "编号",
            "alias_columns": ["可用于"],
            "parameter_template": "{分类}_{编号}",
        }
    }
    variant_file = updater.config.paths.param_config_dir / "variant_data.xlsx"
    with pd.ExcelWriter(variant_file, engine="openpyxl") as writer:
        pd.DataFrame(
            {
                "ExcelParam": ["疑惑三"],
                "ScenarioParam": [None],
                "分类": ["question"],
                "编号": [3],
                "可用于": ["困惑;担忧"],
                "眉毛": ["单侧抬起"],
            }
        ).to_excel(writer, sheet_name="角色B", index=False)

    document = updater.build_agent_variant_document()
    role = document["sheets"]["角色B"]

    assert "question_3" in role["variants"]
    assert role["selection_index"]["groups"]["question"]["3"] == [
        "question_3"
    ]
    assert role["applicability_index"]["困惑"] == ["question_3"]


def test_agent_variant_export_skips_identical_save(tmp_path, monkeypatch):
    updater = _updater(tmp_path)
    variant_file = updater.config.paths.param_config_dir / "variant_data.xlsx"
    with pd.ExcelWriter(variant_file, engine="openpyxl") as writer:
        pd.DataFrame(
            {
                "ExcelParam": ["微笑一"],
                "ScenarioParam": ["smile1"],
                "情绪": ["smile"],
                "序号": [1],
            }
        ).to_excel(writer, sheet_name="角色A", index=False)

    assert updater.export_agent_variant_document() is True
    output_file = updater.config.paths.param_config_dir / "variant_agent_data.json"

    def fail_write(*args, **kwargs):
        raise AssertionError("内容相同时不应再次写入")

    monkeypatch.setattr(type(output_file), "write_text", fail_write)
    assert updater.export_agent_variant_document() is True


def test_agent_variant_export_rejects_missing_composition_value(tmp_path):
    updater = _updater(tmp_path)
    variant_file = updater.config.paths.param_config_dir / "variant_data.xlsx"
    with pd.ExcelWriter(variant_file, engine="openpyxl") as writer:
        pd.DataFrame(
            {
                "ExcelParam": ["未分类一"],
                "ScenarioParam": [None],
                "情绪": [None],
                "序号": [1],
            }
        ).to_excel(writer, sheet_name="角色A", index=False)

    assert updater.export_agent_variant_document() is False
    assert not (
        updater.config.paths.param_config_dir / "variant_agent_data.json"
    ).exists()
