from pathlib import Path

from core.config_manager import AppConfig
from core.resource_extractor import ResourceExtractor
from core.resource_validator import ResourceValidator
from engines.naninovel.resource_resolver import NaninovelDeclarationResolver


class DummyTranslator:
    def __init__(self, mappings=None):
        self.mappings = mappings or {}

    def has_mapping(self, mapping_type, value):
        return (mapping_type, value) in self.mappings

    def translate(self, mapping_type, value):
        return self.mappings[(mapping_type, value)]


def make_extractor(translator=None):
    extractor = ResourceExtractor.__new__(ResourceExtractor)
    extractor.translator = translator or DummyTranslator()
    return extractor


def test_resource_config_roundtrip(tmp_path):
    config = AppConfig.from_dict({
        "engine": {
            "engine_type": "naninovel",
            "declaration_files": {
                "Character": {"Hero": "declarations/hero.txt"},
            },
        },
        "resources": {
            "project_root": "./game",
            "source_root": "./source",
            "validate_source": False,
            "filename_normalization": {
                "音频": ["spaces_to_underscores"],
            },
        },
    })
    config_path = tmp_path / "config.yaml"

    config.to_file(config_path)
    loaded = AppConfig.from_file(config_path)

    assert loaded.resources.validate_source is False
    assert loaded.resources.filename_normalization == {
        "音频": ["spaces_to_underscores"],
    }
    assert loaded.engine.declaration_files == {
        "Character": {"Hero": "declarations/hero.txt"},
    }


def test_extractor_ignores_control_values_before_and_after_translation():
    config = {
        "resource_type": "Music",
        "main_param": "Music",
        "part_params": [],
        "ignore_values": ["停止", "stop"],
    }
    extractor = make_extractor(
        DummyTranslator({("Music", "结束播放"): "stop"})
    )

    assert extractor._build_resource_name_standard({"Music": "停止"}, config) == ""
    assert extractor._build_resource_name_standard({"Music": "结束播放"}, config) == ""


def test_project_only_validation_normalizes_audio_filename(tmp_path):
    project_root = tmp_path / "project"
    audio_folder = project_root / "Audio" / "Music"
    audio_folder.mkdir(parents=True)
    (audio_folder / "Flying_at_spring_night.ogg").write_bytes(b"")
    validator = ResourceValidator(
        project_root,
        tmp_path / "unused_source",
        {"音频": [".ogg"]},
        validate_source=False,
        filename_normalization={"音频": ["spaces_to_underscores"]},
    )

    results = validator.validate_resources(
        {"音频": {"Music": {"Flying at spring night", "Missing track"}}},
        {"Music": "Audio/Music"},
    )

    comparison = results["comparison"]["Music"]
    assert results["source_enabled"] is False
    assert comparison["project_found"] == ["Flying at spring night"]
    assert comparison["project_missing"] == ["Missing track"]
    assert comparison["source_missing"] == []
    assert comparison["missing_in_both"] == []
    assert comparison["project_normalized_matches"] == [{
        "resource_name": "Flying at spring night",
        "found_file": "Flying_at_spring_night.ogg",
        "match_type": "filename_normalization",
        "match_label": "空格转下划线",
    }]


def test_declared_resource_requires_prefab_and_exact_member(tmp_path):
    project_root = tmp_path / "project"
    character_folder = project_root / "Characters"
    character_folder.mkdir(parents=True)
    (character_folder / "Hero.prefab").write_text("prefab", encoding="utf-8")
    declaration = project_root / "declarations" / "hero.txt"
    declaration.parent.mkdir()
    declaration.write_text("idle\nsmile\n", encoding="utf-8")
    validator = ResourceValidator(
        project_root,
        tmp_path / "unused_source",
        {"图片": [".png"]},
        validate_source=False,
        resource_resolvers=[NaninovelDeclarationResolver(
            project_root,
            {"Character": {"Hero": "declarations/hero.txt"}},
        )],
    )

    results = validator.validate_resources(
        {"图片": {"Character": {"Hero/smile", "Hero/smile_extra"}}},
        {"Character": "Characters"},
    )

    comparison = results["comparison"]["Character"]
    assert comparison["project_found"] == ["Hero/smile"]
    assert comparison["project_missing"] == ["Hero/smile_extra"]
    assert comparison["project_resolver_matches"] == [{
        "resource_name": "Hero/smile",
        "found_file": "Hero.prefab|hero.txt#smile",
        "match_type": "naninovel_declaration",
        "match_label": "Naninovel 声明",
    }]
