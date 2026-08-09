from core.config_manager import AppConfig
from tools.validate_resources import (
    generate_report,
    get_resource_resolvers,
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
