from typing import Any, Dict, Optional

from core.sentence_generator_manager import SentenceGeneratorManager
from engines.utage.config import UtageConfig
from engines.utage.generator_base import UtageGeneratorBase


class StubTranslator:
    def translate(self, param_type, value):
        return value

    def has_mapping(self, param_type, value):
        return False


class DummyUtageGenerator(UtageGeneratorBase):
    param_config = {
        "Value": {
            "key": "Arg1",
            "default": "fallback",
        }
    }

    @property
    def category(self) -> str:
        return "Dummy"

    def process(self, data: Dict[str, Any]) -> Optional[list]:
        return None


def make_generator() -> DummyUtageGenerator:
    return DummyUtageGenerator(StubTranslator(), UtageConfig())


def test_creates_command_row():
    generator = make_generator()

    assert generator.create_command("Bg") == {"Command": "Bg"}


def test_sets_configured_parameter_and_default():
    generator = make_generator()
    line = generator.create_command()

    generator.set_param(line, "Value", {"Value": "forest"})
    assert line == {"Arg1": "forest"}

    default_line = generator.create_command()
    generator.set_param(default_line, "Value", {}, use_default=True)
    assert default_line == {"Arg1": "fallback"}


def test_wait_type_is_supported_for_receive_all_generators():
    generator = make_generator()
    line = generator.create_command("MacroCall")

    generator.set_wait_type(line, {"WaitType": "NoWait"})

    assert line == {"Command": "MacroCall", "WaitType": "NoWait"}


def test_missing_wait_type_is_ignored_without_param_config_entry():
    generator = make_generator()
    line = generator.create_command()

    generator.set_wait_type(line, {})

    assert line == {}


def test_state_effects_are_opt_in():
    generator = make_generator()

    assert generator.state_effects({"Value": "forest"}) == []


def test_manager_discovers_all_utage_generators_through_engine_base():
    manager = SentenceGeneratorManager("utage")
    manager.load()

    generators = manager.create_generator_instances(StubTranslator(), UtageConfig())

    assert {type(generator).__name__ for generator in generators} == {
        "AudioGenerator",
        "BackgroundGenerator",
        "CameraGenerator",
        "CharacterTextGenerator",
        "DirectCommandGenerator",
        "FadeGenerator",
        "MacroGenerator",
        "SpriteGenerator",
        "WaitGenerator",
    }
    assert all(isinstance(generator, UtageGeneratorBase) for generator in generators)
