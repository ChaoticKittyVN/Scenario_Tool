"""Generate LetsGal music and sound code."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from engines.letsgal.generator_base import LetsGalGeneratorBase


@dataclass(frozen=True)
class AudioChannel:
    param_name: str
    keyword: str
    loop_config: str


class AudioGenerator(LetsGalGeneratorBase):
    """Render separate table audio channels without JSON option cells."""

    resource_config_music = {
        "resource_type": "Music",
        "resource_category": "音频",
        "main_param": "Music",
        "part_params": [],
        "separator": "",
        "folder": "Audio/Music/",
    }
    resource_config_sound = {
        "resource_type": "Sound",
        "resource_category": "音频",
        "main_param": "Sound",
        "part_params": [],
        "separator": "",
        "folder": "Audio/Sound/",
    }

    param_config = {
        "Music": {},
        "Sound": {},
        "Volume": {},
        "AudioFade": {},
        "AudioLoop": {},
        "MusicLoop": {},
        "SoundLoop": {},
    }

    CHANNELS = (
        AudioChannel("Music", "music", "music_loop"),
        AudioChannel("Sound", "sound", "sound_loop"),
    )

    @property
    def category(self) -> str:
        return "Audio"

    @property
    def priority(self) -> int:
        return 100

    def can_process(self, data: Dict[str, Any]) -> bool:
        return any(not self.is_empty(data.get(channel.param_name)) for channel in self.CHANNELS)

    def _loop(self, channel: AudioChannel, data: Dict[str, Any]) -> bool:
        explicit = self.first_value(
            data,
            (f"{channel.param_name}Loop", "AudioLoop"),
        )
        default = bool(getattr(self.engine_config, channel.loop_config, False))
        return bool(self.normalize_bool(explicit, default=default))

    def _line(self, channel: AudioChannel, value: Any, data: Dict[str, Any]) -> str:
        value_text = str(value).strip()
        if value_text.lower() == "stop" or value_text in {"停止", "关闭"}:
            line = f"stop {channel.keyword}"
            fade = self.first_value(data, ("AudioFade",))
            if not self.is_empty(fade):
                line += f" fadeout {self.normalize_number(fade, field='AudioFade')}"
            return line

        tokens = ["play", channel.keyword, value_text]
        volume = self.first_value(data, ("Volume",))
        if not self.is_empty(volume):
            tokens.extend(["volume", self.percent(volume)])
        if self._loop(channel, data):
            tokens.append("loop")
        fade = self.first_value(data, ("AudioFade",))
        if not self.is_empty(fade):
            tokens.extend(["fadein", self.normalize_number(fade, field="AudioFade")])
        return " ".join(tokens)

    def process(self, data: Dict[str, Any]) -> Optional[list[str]]:
        if not self.can_process(data):
            return None
        return [
            self._line(channel, data[channel.param_name], data)
            for channel in self.CHANNELS
            if not self.is_empty(data.get(channel.param_name))
        ]
