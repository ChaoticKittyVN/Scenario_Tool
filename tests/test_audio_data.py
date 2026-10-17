"""Audio sources must agree across mappings, workbook candidates and Agent data."""

import json
from datetime import date
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

import pytest
from openpyxl import Workbook, load_workbook

from core.config_manager import AppConfig
from core.param_update import ParamUpdater
from core.param_update.audio_data import read_audio_source
from core.param_process.param_translator import ParamTranslator
from core.resource_extractor import ResourceExtractor
from core.sentence_generator_manager import SentenceGeneratorManager
from update_param import main, parse_args


def _write_workbook(path, sheets):
    workbook = Workbook()
    workbook.remove(workbook.active)
    for title, rows in sheets.items():
        sheet = workbook.create_sheet(title)
        for row in rows:
            sheet.append(row)
    workbook.save(path)
    workbook.close()
    return path


def _audio_rows(excel_param="测试配乐", scenario_param="test_cue"):
    return [["ExcelParam", "ScenarioParam"], [excel_param, scenario_param]]


def _updater(tmp_path, engine="renpy", enabled=True, projects=None, multi=False):
    config = AppConfig.from_dict(
        {
            "engine": {"engine_type": engine},
            "audio_data": {"enabled": enabled},
            "projects": projects or {},
            "processing": {"multi_project_mode": multi},
            "paths": {
                "param_config_dir": str(tmp_path / "param_config"),
                "input_dir": str(tmp_path / "input"),
            },
        }
    )
    config.paths.param_config_dir.mkdir()
    config.paths.input_dir.mkdir()
    updater = ParamUpdater(config)
    _write_workbook(
        updater._default_param_file(),
        {"Background": _audio_rows("测试背景", "test_background")},
    )
    return updater


def _mappings(updater):
    namespace = {}
    exec(
        (updater.config.paths.param_config_dir / "param_mappings.py").read_text(
            encoding="utf-8"
        ),
        namespace,
    )
    return namespace["PARAM_MAPPINGS"]


def _candidate_values(path, audio_type):
    workbook = load_workbook(path, read_only=True)
    try:
        rows = list(workbook["参数表"].values)
        column = rows[0].index(audio_type)
        return [row[column] for row in rows[1:] if row[column] is not None]
    finally:
        workbook.close()


@pytest.mark.parametrize("stray_audio_file", [False, True])
def test_disabled_source_preserves_legacy_audio(tmp_path, stray_audio_file):
    updater = _updater(tmp_path, enabled=False)
    _write_workbook(
        updater._default_param_file(), {"Music": _audio_rows("旧音乐", "old_music")}
    )
    if stray_audio_file:
        (updater.config.paths.param_config_dir / "audio_data.xlsx").write_bytes(
            b"invalid"
        )
    assert updater.update_mappings(update_parameter_sheets=False)
    assert _mappings(updater)["Music"] == {"旧音乐": "old_music"}
    assert updater.collect_validation_data(updater._default_param_file())["Music"] == [
        "旧音乐"
    ]
    assert updater.export_audio_document() is False


@pytest.mark.parametrize("engine", ["renpy", "naninovel"])
def test_full_update_uses_one_source_for_mappings_candidates_and_resources(
    tmp_path, engine
):
    updater = _updater(tmp_path, engine=engine)
    updater.config.audio_doc_export.enabled = True
    param_dir = updater.config.paths.param_config_dir
    _write_workbook(
        param_dir / "audio_data.xlsx",
        {
            audio_type: _audio_rows(f"测试{audio_type}", f"test_{audio_type.lower()}")
            for audio_type in ("Music", "Ambience", "Sound")
        },
    )
    scenario = _write_workbook(
        updater.config.paths.input_dir / "scenario.xlsx",
        {
            "场景": [
                ["Music", "Ambience", "Sound"],
                ["测试Music", "测试Ambience", "测试Sound"],
            ],
        },
    )
    assert updater.update_mappings([scenario])
    mappings = _mappings(updater)
    document = json.loads((param_dir / "audio_doc.json").read_text(encoding="utf-8"))
    translator = ParamTranslator(
        str(param_dir / "param_mappings.py"), str(param_dir / "variant_mappings.py")
    )
    manager = SentenceGeneratorManager(engine)
    manager.load()
    extractor = ResourceExtractor(manager, translator, updater.config.engine)
    extractor.setup()
    resources = extractor.extract_from_row(
        {"Music": "测试Music", "Ambience": "测试Ambience", "Sound": "测试Sound"}
    )
    for audio_type in ("Music", "Ambience", "Sound"):
        record = document["default"]["types"][audio_type]["records"][
            f"测试{audio_type}"
        ]
        assert record["scenario_param"] == mappings[audio_type][f"测试{audio_type}"]
        assert _candidate_values(scenario, audio_type) == [f"测试{audio_type}"]
        assert (
            translator.translate(audio_type, f"测试{audio_type}")
            == f"test_{audio_type.lower()}"
        )
        assert resources[audio_type] == {f"test_{audio_type.lower()}"}
    assert mappings["Background"] == {"测试背景": "test_background"}


def test_adoption_is_per_type_and_empty_sheets_also_take_ownership(tmp_path):
    updater = _updater(tmp_path)
    param_dir = updater.config.paths.param_config_dir
    _write_workbook(
        updater._default_param_file(),
        {
            "Sound": _audio_rows("旧音效", "old_sound"),
            "Music": [["ExcelParam", "ScenarioParam"]],
            "Voice": _audio_rows("旧语音", "voice_old"),
        },
    )
    _write_workbook(
        param_dir / "audio_data.xlsx",
        {
            "Music": _audio_rows(),
            "Ambience": [["ExcelParam", "ScenarioParam"]],
        },
    )
    assert updater.generate_param_mappings()
    assert _mappings(updater) == {
        "Sound": {"旧音效": "old_sound"},
        "Voice": {"旧语音": "voice_old"},
        "Music": {"测试配乐": "test_cue"},
        "Ambience": {},
    }


@pytest.mark.parametrize(
    "old_rows",
    [
        _audio_rows(),
        _audio_rows("其他配乐", "other_cue"),
        [["ExcelParam", "ScenarioParam"], ["孤立旧参数", None]],
    ],
)
def test_legacy_rows_conflict_even_when_identical_or_disjoint(tmp_path, old_rows):
    updater = _updater(tmp_path)
    _write_workbook(updater._default_param_file(), {"Music": old_rows})
    _write_workbook(
        updater.config.paths.param_config_dir / "audio_data.xlsx",
        {"Music": _audio_rows()},
    )
    with pytest.raises(ValueError, match="不得保留同类型数据"):
        updater.collect_validation_data(updater._default_param_file())
    assert updater.generate_param_mappings() is False
    assert updater.export_audio_document() is False


@pytest.mark.parametrize("failure", ["missing", "corrupt", "missing_sheet", "missing_column"])
def test_enabled_invalid_source_fails_before_writes_without_fallback(tmp_path, failure):
    updater = _updater(tmp_path, projects={"selected": "测试"})
    param_dir = updater.config.paths.param_config_dir
    audio_file = param_dir / "audio_data_selected.xlsx"
    if failure == "corrupt":
        audio_file.write_bytes(b"invalid workbook")
    elif failure == "missing_sheet":
        _write_workbook(audio_file, {"项目说明": [["说明"], ["没有音频工作表"]]})
    elif failure == "missing_column":
        _write_workbook(audio_file, {"Music": [["ExcelParam"], ["测试"]]})
    if failure != "missing":
        _write_workbook(param_dir / "audio_data.xlsx", {"Music": _audio_rows()})
    mapping_file = param_dir / "param_mappings.py"
    mapping_file.write_text("PARAM_MAPPINGS = {'sentinel': {}}\n", encoding="utf-8")
    output_file = param_dir / "audio_doc.json"
    output_file.write_text('{"sentinel": true}\n', encoding="utf-8")
    scenario = _write_workbook(
        updater.config.paths.input_dir / "scenario.xlsx", {"场景": [["Text"], ["保留"]]}
    )
    original_scenario = scenario.read_bytes()
    assert updater.update_mappings([scenario]) is False
    assert updater.sync_parameter_sheets([scenario]) is False
    assert updater.export_audio_document() is False
    assert (
        mapping_file.read_text(encoding="utf-8")
        == "PARAM_MAPPINGS = {'sentinel': {}}\n"
    )
    assert output_file.read_text(encoding="utf-8") == '{"sentinel": true}\n'
    assert scenario.read_bytes() == original_scenario


@pytest.mark.parametrize(
    "rows, error",
    [
        (
            [["ExcelParam", "ScenarioParam"], ["重复", "one"], ["重复", "one"]],
            "重复 ExcelParam",
        ),
        (
            [["ExcelParam", "ScenarioParam"], ["重复", "one"], ["重复", "two"]],
            "重复 ExcelParam",
        ),
        ([["ExcelParam", "ScenarioParam"], ["缺值", None]], "ScenarioParam"),
        ([["ExcelParam", "ScenarioParam"], [None, "orphan"]], "ExcelParam"),
        (
            [["ExcelParam", "ScenarioParam", "Description"], [None, None, "孤立描述"]],
            "ExcelParam",
        ),
        (
            [
                ["ExcelParam", "ScenarioParam", "Description"],
                ["测试", "cue", "#VALUE!"],
            ],
            "错误值",
        ),
        (
            [["ExcelParam", "ScenarioParam", "ExcelParam"], ["测试", "cue", "重复列"]],
            "重复列名",
        ),
        (
            [["ExcelParam", "ScenarioParam", None], ["测试", "cue", "无标题"]],
            "没有列名",
        ),
    ],
)
def test_invalid_audio_rows_are_rejected_with_location(tmp_path, rows, error):
    path = _write_workbook(tmp_path / "audio_data.xlsx", {"Music": rows})
    with pytest.raises(ValueError, match=error) as caught:
        read_audio_source(path)
    assert "audio_data.xlsx/Music" in str(caught.value)


@pytest.mark.parametrize("sheet_name", ["Musc", "Voice", "Music ", "项目词表"])
def test_non_audio_sheets_are_ignored(tmp_path, sheet_name):
    path = _write_workbook(
        tmp_path / "audio_data.xlsx",
        {"Music": _audio_rows(), sheet_name: [["项目说明"], ["附加资料"]]},
    )
    assert set(read_audio_source(path).sheets) == {"Music"}


@pytest.mark.parametrize("alias, call", [(" 首尾空白", "cue"), ("测试", "cue ")])
def test_mapping_values_follow_the_normal_parameter_reader(tmp_path, alias, call):
    updater = _updater(tmp_path)
    path = _write_workbook(tmp_path / "audio_data.xlsx", {"Music": _audio_rows(alias, call)})
    assert read_audio_source(path).mappings() == updater.read_param_file(path)


def test_formulas_use_the_same_saved_values_as_normal_parameters(tmp_path):
    updater = _updater(tmp_path)
    path = _write_workbook(
        tmp_path / "audio_data.xlsx",
        {"Music": [["ExcelParam", "ScenarioParam", "情绪色彩"], ["缓存公式", "=1+1", "=1+1"]]},
    )
    with ZipFile(path) as archive:
        contents = {name: archive.read(name) for name in archive.namelist()}
    sheet_xml = ElementTree.fromstring(contents["xl/worksheets/sheet1.xml"])
    namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    cached_value = sheet_xml.find(f".//{namespace}c[@r='B2']/{namespace}v")
    assert cached_value is not None
    cached_value.text = "2"
    contents["xl/worksheets/sheet1.xml"] = ElementTree.tostring(sheet_xml, encoding="utf-8")
    with ZipFile(path, "w") as archive:
        for name, content in contents.items():
            archive.writestr(name, content)
    source = read_audio_source(path)
    assert source.mappings() == updater.read_param_file(path)
    assert source.mappings()["Music"] == {"缓存公式": "2"}
    assert source.sheets["Music"]["缓存公式"]["attributes"]["情绪色彩"] is None


def test_uncached_formula_in_a_required_mapping_is_a_missing_value(tmp_path):
    path = _write_workbook(
        tmp_path / "audio_data.xlsx", {"Music": _audio_rows("未保存缓存", "=1+1")}
    )
    with pytest.raises(ValueError, match="ScenarioParam"):
        read_audio_source(path)


def test_metadata_aliases_and_source_descriptions_are_preserved(tmp_path):
    updater = _updater(tmp_path)
    headers = [
        "ExcelParam",
        "ScenarioParam",
        "Description",
        "UsageLimits",
        "Associations",
        "ConfirmedUses",
        "Evidence",
        "VerificationStatus",
        "自定义资料",
        "DurationSeconds",
        "核实日期",
    ]
    _write_workbook(
        updater.config.paths.param_config_dir / "audio_data.xlsx",
        {
            "Music": [
                headers,
                [
                    "别名一",
                    "cue",
                    "文件名推测，未试听",
                    "需确认",
                    "测试场景",
                    "测试用例；理由待复核",
                    "客户文件清单",
                    None,
                    "中文扩展列",
                    0,
                    date(2026, 10, 17),
                ],
                [
                    "别名二",
                    "cue",
                    "测试描述",
                    None,
                    None,
                    None,
                    "人工测试核实记录",
                    "verified",
                    None,
                    None,
                    None,
                ],
            ],
        },
    )
    document = updater.build_audio_document()
    music = document["default"]["types"]["Music"]
    record = music["records"]["别名一"]
    assert music["scenario_index"] == {"cue": ["别名一", "别名二"]}
    assert music["records"]["别名二"]["attributes"]["VerificationStatus"] == "verified"
    assert record["attributes"]["Description"] == "文件名推测，未试听"
    assert record["attributes"]["自定义资料"] == "中文扩展列"
    assert record["attributes"]["DurationSeconds"] == 0
    assert record["attributes"]["核实日期"].startswith("2026-10-17")
    assert record["attributes"]["VerificationStatus"] is None
    assert record["attributes"]["UsageLimits"] == "需确认"
    assert record["source_row"] == 2


def test_single_project_uses_common_file_when_specific_file_is_missing(tmp_path):
    updater = _updater(tmp_path, projects={"chapter_a": "第一篇"})
    param_dir = updater.config.paths.param_config_dir
    _write_workbook(
        param_dir / "audio_data.xlsx", {"Music": _audio_rows("公共", "global")}
    )
    scenario = _write_workbook(
        updater.config.paths.input_dir / "第一篇.xlsx", {"场景": [["Music"]]}
    )
    updater.config.audio_doc_export.enabled = True
    assert updater.update_mappings([scenario])
    document = json.loads((param_dir / "audio_doc.json").read_text(encoding="utf-8"))
    scope = document["projects"]["chapter_a"]
    assert scope["source_files"] == [str(param_dir / "audio_data.xlsx")]
    assert scope["types"]["Music"]["records"]["公共"]["scenario_param"] == "global"
    assert _mappings(updater)["Music"] == {"公共": "global"}
    assert _candidate_values(scenario, "Music") == ["公共"]


def test_single_project_specific_file_replaces_the_common_source(tmp_path):
    updater = _updater(tmp_path, projects={"chapter_a": "第一篇"})
    param_dir = updater.config.paths.param_config_dir
    common = param_dir / "audio_data.xlsx"
    _write_workbook(common, {"Music": _audio_rows("公共", "global")})
    _write_workbook(
        param_dir / "audio_data_chapter_a.xlsx",
        {"Music": _audio_rows("项目", "project")},
    )
    assert updater.build_audio_document()["projects"]["chapter_a"]["types"]["Music"][
        "records"
    ].keys() == {"项目"}
    common.write_bytes(b"unselected common file is invalid")
    document = updater.build_audio_document()
    assert document["default"] is None
    assert document["projects"]["chapter_a"]["types"]["Music"]["records"].keys() == {
        "项目"
    }
    assert updater.generate_param_mappings()
    assert _mappings(updater)["Music"] == {"项目": "project"}


@pytest.mark.parametrize("engine", ["renpy", "naninovel"])
def test_engine_names_do_not_participate_in_audio_source_selection(tmp_path, engine):
    updater = _updater(tmp_path, engine=engine, projects={"chapter_a": "第一篇"})
    param_dir = updater.config.paths.param_config_dir
    for filename in (
        f"audio_data_{engine}.xlsx",
        f"audio_data_{engine}_chapter_a.xlsx",
    ):
        _write_workbook(param_dir / filename, {"Music": _audio_rows("旧名称", "old")})
    with pytest.raises(FileNotFoundError, match="audio_data_chapter_a.xlsx"):
        updater.build_audio_document()
    common = _write_workbook(param_dir / "audio_data.xlsx", {"Music": _audio_rows()})
    assert updater._audio_data_file("chapter_a") == common
    assert updater._audio_data_file() == common
    assert updater.generate_param_mappings()
    assert _mappings(updater)["Music"] == {"测试配乐": "test_cue"}


def test_multi_project_common_and_specific_sources_agree_across_all_outputs(tmp_path):
    updater = _updater(tmp_path, projects={"a": "甲篇", "b": "乙篇"}, multi=True)
    param_dir = updater.config.paths.param_config_dir
    headers = ["ExcelParam", "ScenarioParam", "叙事用途", "项目扩展"]
    common = _write_workbook(
        param_dir / "audio_data.xlsx",
        {"Music": [headers, ["共享", "shared", "通用说明", "共享扩展"]]},
    )
    specific = _write_workbook(
        param_dir / "audio_data_a.xlsx",
        {
            "Music": [
                headers,
                ["共享", "shared", "项目说明", None],
                ["甲配乐", "cue_a", None, "甲扩展"],
            ]
        },
    )
    first = _write_workbook(
        updater.config.paths.input_dir / "甲篇.xlsx", {"场景": [["Music"]]}
    )
    second = _write_workbook(
        updater.config.paths.input_dir / "乙篇.xlsx", {"场景": [["Music"]]}
    )
    updater.config.audio_doc_export.enabled = True
    assert updater.update_mappings([first, second])
    assert _mappings(updater)["Music"] == {"共享": "shared", "甲配乐": "cue_a"}
    assert _candidate_values(first, "Music") == ["共享", "甲配乐"]
    assert _candidate_values(second, "Music") == ["共享"]
    document = json.loads((param_dir / "audio_doc.json").read_text(encoding="utf-8"))
    assert document["default"]["source_files"] == [str(common)]
    assert document["projects"]["a"]["source_files"] == [str(common), str(specific)]
    assert document["projects"]["b"]["source_files"] == [str(common)]
    for project, expected in (("a", ["共享", "甲配乐"]), ("b", ["共享"])):
        records = document["projects"][project]["types"]["Music"]["records"]
        assert list(records) == expected
        for alias, record in records.items():
            assert record["scenario_param"] == _mappings(updater)["Music"][alias]
    first_record = document["projects"]["a"]["types"]["Music"]["records"]["共享"]
    second_record = document["projects"]["b"]["types"]["Music"]["records"]["共享"]
    assert first_record["attributes"] == {"叙事用途": "项目说明", "项目扩展": None}
    assert first_record["source_file"] == str(specific)
    assert second_record["attributes"]["叙事用途"] == "通用说明"
    assert second_record["source_file"] == str(common)


def test_common_project_override_reuses_the_normal_mapping_merge(tmp_path):
    updater = _updater(tmp_path, projects={"a": "甲篇"}, multi=True)
    param_dir = updater.config.paths.param_config_dir
    _write_workbook(
        param_dir / "audio_data.xlsx", {"Music": _audio_rows("同名", "common")}
    )
    _write_workbook(
        param_dir / "audio_data_a.xlsx", {"Music": _audio_rows("同名", "specific")}
    )
    expected = updater._merge_mappings(
        [{"Music": {"同名": "common"}}, {"Music": {"同名": "specific"}}]
    )
    assert updater.generate_param_mappings()
    assert _mappings(updater)["Music"] == expected["Music"]
    default_record = updater.build_audio_document()["default"]["types"]["Music"][
        "records"
    ]["同名"]
    assert default_record["scenario_param"] == "specific"
    assert default_record["source_file"] == str(param_dir / "audio_data_a.xlsx")
    assert updater._with_audio_validation({}, None)["Music"] == ["同名"]
    assert (
        updater.build_audio_document()["projects"]["a"]["types"]["Music"]["records"][
            "同名"
        ]["scenario_param"]
        == "specific"
    )


def test_shared_fallback_uses_the_normal_global_mapping_override(tmp_path, caplog):
    updater = _updater(tmp_path, projects={"a": "甲篇", "b": "乙篇"}, multi=True)
    param_dir = updater.config.paths.param_config_dir
    _write_workbook(
        param_dir / "audio_data.xlsx", {"Music": _audio_rows("同名", "common")}
    )
    _write_workbook(
        param_dir / "audio_data_a.xlsx", {"Music": _audio_rows("同名", "specific")}
    )
    assert updater.generate_param_mappings()
    assert _mappings(updater)["Music"] == {"同名": "specific"}
    document = updater.build_audio_document()
    for project in ("a", "b"):
        record = document["projects"][project]["types"]["Music"]["records"]["同名"]
        assert record["scenario_param"] == "specific"
        assert record["source_file"] == str(param_dir / "audio_data_a.xlsx")
        assert updater._with_audio_validation({}, project)["Music"] == ["同名"]
    assert "普通参数的全局覆盖规则" in caplog.text


@pytest.mark.parametrize("invalid_file", ["audio_data.xlsx", "audio_data_a.xlsx"])
def test_multi_project_invalid_selected_file_never_falls_back(tmp_path, invalid_file):
    updater = _updater(tmp_path, projects={"a": "甲篇", "b": "乙篇"}, multi=True)
    param_dir = updater.config.paths.param_config_dir
    for filename in ("audio_data.xlsx", "audio_data_a.xlsx", "audio_data_b.xlsx"):
        _write_workbook(param_dir / filename, {"Music": _audio_rows()})
    (param_dir / invalid_file).write_bytes(b"corrupt selected source")
    assert updater.generate_param_mappings() is False
    assert updater.export_audio_document() is False
    assert not (param_dir / "param_mappings.py").exists()


def test_multi_project_sources_stay_separate_in_candidates_and_agent_records(tmp_path):
    updater = _updater(tmp_path, projects={"a": "甲篇", "b": "乙篇"}, multi=True)
    param_dir = updater.config.paths.param_config_dir
    _write_workbook(
        param_dir / "audio_data_a.xlsx", {"Music": _audio_rows("甲配乐", "cue_a")}
    )
    _write_workbook(
        param_dir / "audio_data_b.xlsx", {"Music": _audio_rows("乙配乐", "cue_b")}
    )
    first = _write_workbook(
        updater.config.paths.input_dir / "甲篇.xlsx", {"场景": [["Music"]]}
    )
    second = _write_workbook(
        updater.config.paths.input_dir / "乙篇.xlsx", {"场景": [["Music"]]}
    )
    assert updater.update_mappings([first, second])
    assert _mappings(updater)["Music"] == {"甲配乐": "cue_a", "乙配乐": "cue_b"}
    assert _candidate_values(first, "Music") == ["甲配乐"]
    assert _candidate_values(second, "Music") == ["乙配乐"]
    document = updater.build_audio_document()
    assert document["default"] is None
    assert document["projects"]["a"]["types"]["Music"]["records"].keys() == {"甲配乐"}
    assert document["projects"]["b"]["types"]["Music"]["records"].keys() == {"乙配乐"}


@pytest.mark.parametrize("same_call", [True, False])
def test_cross_project_same_alias_follows_normal_mapping_order(tmp_path, same_call):
    updater = _updater(tmp_path, projects={"a": "甲篇", "b": "乙篇"}, multi=True)
    param_dir = updater.config.paths.param_config_dir
    _write_workbook(
        param_dir / "audio_data_a.xlsx",
        {"Music": [["ExcelParam", "ScenarioParam", "情绪色彩"], ["共享参数", "cue", "甲资源描述"]]},
    )
    _write_workbook(
        param_dir / "audio_data_b.xlsx",
        {
            "Music": [
                ["ExcelParam", "ScenarioParam", "情绪色彩"],
                ["共享参数", "cue" if same_call else "other_cue", "乙资源描述"],
            ]
        },
    )
    assert updater.generate_param_mappings()
    expected = "cue" if same_call else "other_cue"
    assert _mappings(updater)["Music"] == {"共享参数": expected}
    document = updater.build_audio_document()
    for project in ("a", "b"):
        record = document["projects"][project]["types"]["Music"]["records"]["共享参数"]
        assert record["scenario_param"] == expected
        assert record["attributes"]["情绪色彩"] == (
            "甲资源描述" if same_call and project == "a" else "乙资源描述"
        )


@pytest.mark.parametrize("filename", ["公共.xlsx", "甲篇乙篇.xlsx"])
def test_multi_project_matching_keeps_normal_common_and_first_match_behavior(
    tmp_path, filename
):
    updater = _updater(tmp_path, projects={"a": "甲篇", "b": "乙篇"}, multi=True)
    param_dir = updater.config.paths.param_config_dir
    _write_workbook(
        param_dir / "audio_data.xlsx", {"Music": _audio_rows("公共", "common")}
    )
    for project in ("a", "b"):
        _write_workbook(
            param_dir / f"audio_data_{project}.xlsx",
            {"Music": _audio_rows(project, f"cue_{project}")},
        )
    scenario = _write_workbook(
        updater.config.paths.input_dir / filename, {"场景": [["Music"]]}
    )
    assert updater.update_mappings([scenario])
    expected = ["公共"] if filename == "公共.xlsx" else ["公共", "a"]
    assert _candidate_values(scenario, "Music") == expected


def test_project_source_missing_does_not_mix_another_project(tmp_path):
    updater = _updater(tmp_path, projects={"a": "甲篇", "b": "乙篇"}, multi=True)
    _write_workbook(
        updater.config.paths.param_config_dir / "audio_data_a.xlsx",
        {"Music": _audio_rows()},
    )
    assert updater.generate_param_mappings() is False
    with pytest.raises(FileNotFoundError, match="audio_data_b.xlsx"):
        updater.build_audio_document()


def test_multiple_projects_require_explicit_multi_project_mode(tmp_path):
    updater = _updater(tmp_path, projects={"a": "甲篇", "b": "乙篇"})
    with pytest.raises(ValueError, match="multi_project_mode"):
        updater.build_audio_document()


def test_audio_export_is_idempotent_and_dry_run_does_not_write(tmp_path, monkeypatch):
    updater = _updater(tmp_path)
    param_dir = updater.config.paths.param_config_dir
    _write_workbook(param_dir / "audio_data.xlsx", {"Music": _audio_rows()})
    updater.config.audio_doc_export.output_file = "agent/audio.json"
    output_file = param_dir / "agent" / "audio.json"
    assert updater.export_audio_document(dry_run=True)
    assert not output_file.exists()
    assert updater.export_audio_document()

    def fail_write(*args, **kwargs):
        raise AssertionError("相同内容不应再次写入")

    monkeypatch.setattr(Path, "write_text", fail_write)
    assert updater.export_audio_document()


@pytest.mark.parametrize(
    "option", ["--mappings-only", "--parameter-sheet-only", "--audio-doc-only"]
)
def test_cli_audio_modes_only_write_the_requested_outputs(
    tmp_path, monkeypatch, option
):
    updater = _updater(tmp_path)
    param_dir = updater.config.paths.param_config_dir
    _write_workbook(param_dir / "audio_data.xlsx", {"Music": _audio_rows()})
    scenario = _write_workbook(
        updater.config.paths.input_dir / "scenario.xlsx", {"场景": [["Music"]]}
    )
    config_file = tmp_path / "config.yaml"
    updater.config.to_file(config_file)
    original = scenario.read_bytes()
    monkeypatch.setattr(
        "sys.argv", ["update_param.py", "--config", str(config_file), option]
    )
    assert main() == 0
    assert (param_dir / "param_mappings.py").exists() is (option == "--mappings-only")
    assert (param_dir / "audio_doc.json").exists() is (option == "--audio-doc-only")
    assert (scenario.read_bytes() != original) is (option == "--parameter-sheet-only")
    if option == "--parameter-sheet-only":
        assert _candidate_values(scenario, "Music") == ["测试配乐"]


def test_audio_cli_flag_and_full_dry_run(tmp_path, monkeypatch):
    updater = _updater(tmp_path)
    param_dir = updater.config.paths.param_config_dir
    _write_workbook(param_dir / "audio_data.xlsx", {"Music": _audio_rows()})
    scenario = _write_workbook(
        updater.config.paths.input_dir / "scenario.xlsx", {"场景": [["Music"]]}
    )
    original = scenario.read_bytes()
    updater.config.audio_doc_export.enabled = True
    assert updater.update_mappings([scenario], dry_run=True)
    assert scenario.read_bytes() == original
    assert not (param_dir / "param_mappings.py").exists()
    assert not (param_dir / "audio_doc.json").exists()
    monkeypatch.setattr("sys.argv", ["update_param.py", "--audio-doc-only"])
    assert parse_args().audio_doc_only is True


def test_auto_export_requires_enabled_audio_source(tmp_path):
    updater = _updater(tmp_path, enabled=False)
    updater.config.audio_doc_export.enabled = True
    assert updater.update_mappings(update_parameter_sheets=False) is False
    assert not (updater.config.paths.param_config_dir / "param_mappings.py").exists()


def test_eight_column_workbook_can_start_with_empty_audio_sheets(tmp_path):
    headers = [
        "ExcelParam",
        "ScenarioParam",
        "情绪色彩",
        "张力与能量",
        "节奏与运动感",
        "音色与风格",
        "发展与结构",
        "叙事用途",
    ]
    path = _write_workbook(
        tmp_path / "audio_data.xlsx",
        {audio_type: [headers] for audio_type in ("Music", "Ambience", "Sound")},
    )
    assert read_audio_source(path).sheets == {"Music": {}, "Ambience": {}, "Sound": {}}


def test_audio_configuration_roundtrip(tmp_path):
    config = AppConfig.from_dict(
        {
            "audio_data": {"enabled": True},
            "audio_doc_export": {"enabled": True, "output_file": "agent/audio.json"},
        }
    )
    config_file = tmp_path / "config.yaml"
    config.to_file(config_file)
    loaded = AppConfig.from_file(config_file)
    assert loaded.audio_data.enabled is True
    assert loaded.audio_doc_export.output_file == "agent/audio.json"
    assert loaded.audio_doc_export.enabled is True
    assert "audio_doc_export" in loaded.to_dict()
    assert "audio_agent_export" not in loaded.to_dict()
    assert AppConfig.create_default("renpy").audio_data.enabled is False


@pytest.mark.parametrize(
    "config",
    [
        {"audio_data": None},
        {"audio_data": {"enabled": "false"}},
        {"audio_doc_export": True},
        {"audio_doc_export": {"enabled": "true"}},
        {"audio_doc_export": {"output_file": " "}},
    ],
)
def test_invalid_audio_configuration_does_not_silently_disable_source(config):
    with pytest.raises(ValueError):
        AppConfig.from_dict(config)


def test_music_dimensions_allow_multiple_labels_development_and_project_extensions(
    tmp_path,
):
    updater = _updater(tmp_path)
    headers = [
        "ExcelParam",
        "ScenarioParam",
        "情绪色彩",
        "张力与能量",
        "节奏与运动感",
        "音色与风格",
        "发展与结构",
        "叙事用途",
        "项目词表维度",
        "DurationSeconds",
        "Loop",
    ]
    values = [
        "维度测试",
        "dimension_cue",
        "温暖；忧伤（后半段）",
        "张力：开头舒缓，中段紧绷；能量：低，保持克制",
        "缓慢流动；中段脉动",
        "音色待核实；测试词表",
        "开头平静、主体稳定、中段紧张、尾部收束，未定位秒数",
        "关系缓和；回忆，理由由项目维护",
        "项目自由词一 / 项目自由词二；文字说明",
        None,
        None,
    ]
    _write_workbook(
        updater.config.paths.param_config_dir / "audio_data.xlsx",
        {"Music": [headers, values]},
    )
    assert updater.export_audio_document()
    document = json.loads(
        (updater.config.paths.param_config_dir / "audio_doc.json").read_text(
            encoding="utf-8"
        )
    )
    record = document["default"]["types"]["Music"]["records"]["维度测试"]
    assert record["attributes"] == dict(zip(headers[2:], values[2:]))
    assert (
        record["attributes"]["张力与能量"]
        == "张力：开头舒缓，中段紧绷；能量：低，保持克制"
    )
    assert record["attributes"]["DurationSeconds"] is None
    assert record["attributes"]["Loop"] is None
    assert record["scenario_param"] == "dimension_cue"
    assert set(record) == {
        "excel_param", "scenario_param", "source_file", "source_row", "attributes"
    }


def test_source_and_verification_descriptions_remain_plain_text(tmp_path):
    updater = _updater(tmp_path)
    headers = ["ExcelParam", "ScenarioParam", "情绪色彩", "叙事用途", "发展与结构", "循环说明"]
    values = [
        "依据测试",
        "description_cue",
        "实际试听：开头平静，中段紧张",
        "用户确认：关系缓和段落可用",
        "素材说明：中段有变化，尚未试听核实",
        "待核实推断：有循环感，接缝未知",
    ]
    _write_workbook(
        updater.config.paths.param_config_dir / "audio_data.xlsx",
        {"Music": [headers, values]},
    )
    document = updater.build_audio_document()
    record = document["default"]["types"]["Music"]["records"]["依据测试"]
    assert record["attributes"] == dict(zip(headers[2:], values[2:]))
    assert set(record) == {
        "excel_param", "scenario_param", "source_file", "source_row", "attributes"
    }
    assert "verification_policy" not in document


@pytest.mark.parametrize("status", ["confirmed", "verified", False, 0, None])
def test_custom_columns_have_no_special_verification_semantics(tmp_path, status):
    updater = _updater(tmp_path)
    attributes = {
        "SourceKind": "项目自己的说明",
        "Evidence": None,
        "VerificationStatus": status,
        "自定义__Evidence": "保留普通扩展列，不要求配套列",
    }
    _write_workbook(
        updater.config.paths.param_config_dir / "audio_data.xlsx",
        {
            "Music": [
                ["ExcelParam", "ScenarioParam", *attributes],
                ["测试", "cue", *attributes.values()],
            ]
        },
    )
    assert updater.export_audio_document()
    document = json.loads(
        (updater.config.paths.param_config_dir / "audio_doc.json").read_text(
            encoding="utf-8"
        )
    )
    record = document["default"]["types"]["Music"]["records"]["测试"]
    assert record["attributes"] == attributes
    assert type(record["attributes"]["VerificationStatus"]) is type(status)
    assert set(record) == {
        "excel_param", "scenario_param", "source_file", "source_row", "attributes"
    }


@pytest.mark.parametrize("audio_type", ["Music", "Ambience", "Sound"])
def test_comparison_dimensions_are_optional_for_every_type(
    tmp_path, audio_type
):
    path = _write_workbook(tmp_path / "audio_data.xlsx", {audio_type: _audio_rows()})
    record = read_audio_source(path).sheets[audio_type]["测试配乐"]
    assert record["attributes"] == {}
    assert set(record) == {
        "excel_param", "scenario_param", "source_file", "source_row", "attributes"
    }


@pytest.mark.parametrize(
    "options",
    [
        [],
        ["--dry-run"],
        ["--mappings-only"],
        ["--parameter-sheet-only"],
        ["--audio-doc-only"],
    ],
)
def test_cli_invalid_enabled_source_returns_failure_and_preserves_workbooks(
    tmp_path, monkeypatch, options
):
    updater = _updater(tmp_path)
    scenario = _write_workbook(
        updater.config.paths.input_dir / "scenario.xlsx", {"场景": [["Music"]]}
    )
    original = scenario.read_bytes()
    config_file = tmp_path / "config.yaml"
    updater.config.to_file(config_file)
    monkeypatch.setattr(
        "sys.argv", ["update_param.py", "--config", str(config_file), *options]
    )
    assert main() == 1
    assert scenario.read_bytes() == original
    assert not (updater.config.paths.param_config_dir / "param_mappings.py").exists()


@pytest.mark.parametrize("enabled", [False, True])
def test_audio_integration_keeps_the_existing_parameter_sync_policy(
    tmp_path, monkeypatch, enabled
):
    updater = _updater(tmp_path, enabled=enabled)
    _write_workbook(
        updater.config.paths.param_config_dir / "audio_data.xlsx",
        {"Music": _audio_rows()},
    )
    monkeypatch.setattr(updater, "sync_parameter_sheets", lambda **kwargs: False)
    assert updater.update_mappings() is True


def test_audio_document_output_cannot_overwrite_the_audio_workbook(tmp_path):
    updater = _updater(tmp_path)
    audio_file = _write_workbook(
        updater.config.paths.param_config_dir / "audio_data.xlsx",
        {"Music": _audio_rows()},
    )
    original = audio_file.read_bytes()
    updater.config.audio_doc_export.output_file = str(audio_file)
    assert updater.export_audio_document() is False
    assert audio_file.read_bytes() == original
