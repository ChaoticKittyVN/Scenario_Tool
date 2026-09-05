"""Tests for the LetsGal Studio code-layer adapter."""

from pathlib import Path

import pandas as pd
import pytest

from core.engine_loader import load_engine
from core.scenario_output import OutputFormat, OutputManager
from engines.letsgal import create_letsgal_processor
from engines.letsgal.config import LetsGalConfig
from engines.letsgal.sentence_generators.audio_generator import AudioGenerator
from engines.letsgal.sentence_generators.ambience_generator import AmbienceGenerator
from engines.letsgal.sentence_generators.character_generator import CharacterGenerator
from engines.letsgal.sentence_generators.scene_generator import SceneGenerator
from engines.letsgal.sentence_generators.text_generator import TextGenerator


class IdentityTranslator:
    def translate(self, param_type, value):
        return value

    def has_mapping(self, param_type, value):
        return False


def make_processor(config=None):
    return create_letsgal_processor(config or LetsGalConfig(), IdentityTranslator())


def test_letsgal_registers_text_code_engine():
    metadata = load_engine("letsgal")

    assert metadata.name == "letsgal"
    assert metadata.file_extension == ".txt"
    assert metadata.config_class is LetsGalConfig


def test_processor_discovers_code_generators_in_output_order():
    processor = make_processor()

    assert [generator.__class__.__name__ for generator in processor.generators] == [
        "NoteGenerator",
        "AudioGenerator",
        "AmbienceGenerator",
        "CameraGenerator",
        "SceneGenerator",
        "CharacterGenerator",
        "PauseGenerator",
        "VoiceGenerator",
        "TextGenerator",
    ]

    names = processor.get_generator_manager().get_all_param_names()
    assert "SceneOptions" not in names
    assert "MusicOptions" not in names
    assert "CharacterId" not in names
    assert "SceneId" not in names


def test_scene_generator_shares_background_and_event_code_shape():
    generator = SceneGenerator(IdentityTranslator(), LetsGalConfig())

    assert generator.process(
        {"Background": "教室", "With": "渐变", "WithAtr": "0.6", "WithWait": "是"}
    ) == ["scene 教室 with fade duration 0.6 wait"]
    assert generator.process({"Event": "日出CG", "EventVariant": "白天"}) == [
        "scene 日出CG 白天"
    ]

    with pytest.raises(ValueError, match="不能在同一行"):
        generator.process({"Background": "教室", "Event": "日出CG"})


def test_character_show_hide_and_repeated_show_need_no_update_command():
    generator = CharacterGenerator(IdentityTranslator(), LetsGalConfig())

    assert generator.process(
        {"Character": "铃铃", "Variant": "开心", "Position": "左"}
    ) == ["show 铃铃 开心 at left"]
    with pytest.raises(ValueError, match="show/显示 或 hide/隐藏"):
        generator.process({"CharacterCommand": "更新", "Character": "铃铃"})
    assert generator.process({"CharacterCommand": "隐藏", "Character": "铃铃"}) == [
        "hide 铃铃"
    ]


def test_audio_has_independent_ambience_channel_and_uses_code_options():
    generator = AudioGenerator(
        IdentityTranslator(),
        LetsGalConfig(music_loop=True, ambience_loop=True, sound_loop=False),
    )
    ambience = AmbienceGenerator(
        IdentityTranslator(),
        LetsGalConfig(music_loop=True, ambience_loop=True, sound_loop=False),
    )

    assert generator.process(
        {
            "Music": "主题曲.ogg",
            "Sound": "铃声.wav",
            "Volume": "80",
            "AudioFade": "0.5",
        }
    ) == [
        "play music 主题曲.ogg volume 80% loop fadein 0.5",
        "play sound 铃声.wav volume 80% fadein 0.5",
    ]
    assert ambience.process(
        {"Ambience": "雨声.ogg", "Volume": "80", "AudioFade": "0.5"}
    ) == ["play sound 雨声.ogg volume 80% loop fadein 0.5"]


def test_numeric_spreadsheet_values_render_without_float_suffixes():
    generator = AudioGenerator(IdentityTranslator(), LetsGalConfig())

    assert generator.process({"Music": "主题曲.ogg", "Volume": 70.0}) == [
        "play music 主题曲.ogg volume 70% loop"
    ]


def test_voice_is_direct_path_and_precedes_dialogue():
    processor = make_processor()

    commands = processor.process_row(
        pd.Series(
            {
                "Voice": "Audio/Voice/铃铃_001.wav",
                "Character": "铃铃",
                "Name": "铃铃",
                "Text": '今天说 "你好"。',
            }
        )
    )

    assert commands == [
        "show 铃铃",
        "play voice Audio/Voice/铃铃_001.wav",
        '铃铃 "今天说 \\\"你好\\\"。"',
    ]


def test_pause_and_camera_use_documented_code_forms():
    processor = make_processor()

    assert processor.process_row(pd.Series({"Pause": "500ms"})) == ["pause 500ms"]
    assert processor.process_row(
        pd.Series(
            {
                "Camera": "move",
                "OffsetX": "120",
                "OffsetY": "-20",
                "Zoom": "1.15",
                "CameraTime": "0.8",
                "CameraEasing": "easeInOut",
                "CameraWait": "是",
            }
        )
    ) == ["camera x 120 y -20 zoom 1.15 duration 0.8 easing easeInOut wait"]


def test_text_output_is_plain_code(tmp_path: Path):
    output = tmp_path / "scene.txt"
    success = OutputManager.create_default().output(
        data=["scene 教室", '铃铃 "你好"'],
        output_path=output,
        format=OutputFormat.TEXT,
        engine_config=LetsGalConfig(),
    )

    assert success
    assert output.read_text(encoding="utf-8") == 'scene 教室\n铃铃 "你好"'
