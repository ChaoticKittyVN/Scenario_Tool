"""Configuration for the LetsGal Studio code layer."""

from dataclasses import dataclass

from core.config_manager import EngineConfig


@dataclass
class LetsGalConfig(EngineConfig):
    """Project-level defaults for generated LetsGal code.

    The generated file is plain text intended for LetsGal Studio's Ren'Py
    style code view. Resource cells are emitted as names or paths; this layer
    deliberately does not introduce UUIDs or a JSON storage contract.
    """

    engine_type: str = "letsgal"
    file_extension: str = ".txt"
    indent_size: int = 0
    use_macro: bool = False

    default_transition: str = ""
    default_transition_duration: str = ""
    default_transition_wait: bool = False

    music_loop: bool = True
    ambience_loop: bool = True
    sound_loop: bool = False
