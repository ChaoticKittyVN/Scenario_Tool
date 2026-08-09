from core.config_manager import AppConfig
from tools.validate_resources import (
    generate_report,
    get_resource_resolvers,
    get_missing_references,
    merge_references,
    merge_resources,
    save_report,
)


def test_report_supports_project_only_mode_and_match_details(tmp_path):
    resources = {"音频": {"Music": {"Flying at spring night", "Missing track"}}}
    validation_results = {
        "source_enabled": False,
        "comparison": {
            "Music": {
                "project_found": ["Flying at spring night"],
                "project_missing": ["Missing track"],
                "source_found": [],
                "source_missing": [],
                "missing_in_project_but_in_source": [],
                "missing_in_both": [],
                "project_normalized_matches": [{
                    "resource_name": "Flying at spring night",
                    "found_file": "Flying_at_spring_night.ogg",
                }],
                "project_resolver_matches": [],
            },
        },
    }

    report = generate_report(resources, validation_results, "chapter.xlsx")

    assert "项目库缺失 (1):" in report
    assert "文件名归一化命中 (1):" in report
    assert "资源库:" not in report

    combined = {}
    merge_resources(combined, resources)
    merge_resources(combined, {"音频": {"Music": {"Another track"}}})
    assert combined["音频"]["Music"] == {
        "Flying at spring night",
        "Missing track",
        "Another track",
    }

    save_report(
        tmp_path,
        "all_workbooks",
        "全部演出表格",
        combined,
        validation_results,
        {"Music": "Audio/Music"},
        tmp_path / "project",
    )
    assert (tmp_path / "all_workbooks_validation.txt").exists()
    assert (tmp_path / "all_workbooks_validation.json").exists()


def test_resource_resolvers_are_created_from_engine_registration():
    renpy_config = AppConfig.from_dict({
        "engine": {"engine_type": "renpy"},
    })
    naninovel_config = AppConfig.from_dict({
        "engine": {
            "engine_type": "naninovel",
            "declaration_files": {
                "Character": {"Hero": "declarations/hero.txt"},
            },
        },
    })

    assert get_resource_resolvers(renpy_config) == []
    resolvers = get_resource_resolvers(naninovel_config)
    assert len(resolvers) == 1
    assert resolvers[0].declaration_files == {
        "Character": {"Hero": "declarations/hero.txt"},
    }


def test_reference_reports_keep_exact_count_and_bounded_samples():
    references = {
        "音频": {
            "Music": {
                "Missing track": {
                    "reference_count": 3,
                    "locations": [{
                        "workbook": "chapter1.xlsx",
                        "sheet": "演出表",
                        "excel_row": 12,
                        "index": "A010",
                        "params": {"Music": "Missing track"},
                    }],
                    "locations_truncated": True,
                },
            },
        },
    }
    more_references = {
        "音频": {
            "Music": {
                "Missing track": {
                    "reference_count": 2,
                    "locations": [{
                        "workbook": "chapter2.xlsx",
                        "sheet": "Scene02",
                        "excel_row": 8,
                        "index": "B004",
                        "params": {"Music": "Missing track"},
                    }],
                    "locations_truncated": True,
                },
            },
        },
    }
    merge_references(references, more_references, sample_limit=1)
    summary = references["音频"]["Music"]["Missing track"]
    assert summary["reference_count"] == 5
    assert len(summary["locations"]) == 1
    assert summary["locations_truncated"] is True

    validation_results = {
        "source_enabled": False,
        "comparison": {
            "Music": {
                "project_found": [],
                "project_missing": ["Missing track"],
                "source_found": [],
                "source_missing": [],
            },
        },
    }
    report = generate_report(
        {"音频": {"Music": {"Missing track"}}},
        validation_results,
        "全部演出表格",
        references,
    )

    assert "引用 5 次，显示 1 处" in report
    assert "Excel 第 12 行 / Index=A010" in report
    assert "其余 4 处未显示" in report
    assert get_missing_references(references, validation_results) == references
