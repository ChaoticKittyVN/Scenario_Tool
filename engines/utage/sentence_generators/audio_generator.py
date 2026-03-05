"""
Utage Audio Generator
生成音频相关命令（音乐、音效、氛围）
"""
from typing import Any, Dict, Optional
from core.dict_based_sentence_generator import DictBasedSentenceGenerator


class AudioGenerator(DictBasedSentenceGenerator):
    """音频生成器"""

    # Music 资源配置
    resource_config_music = {
        "resource_type": "Music",
        "resource_category": "音频",
        "main_param": "Music",
        "part_params": [],
        "separator": "",
        "folder": "audio/Music/"
    }

    # Sound 资源配置
    resource_config_sound = {
        "resource_type": "Sound",
        "resource_category": "音频",
        "main_param": "Sound",
        "part_params": [],
        "separator": "",
        "folder": "audio/Sound/"
    }

    # Ambience 资源配置
    resource_config_ambience = {
        "resource_type": "Ambience",
        "resource_category": "音频",
        "main_param": "Ambience",
        "part_params": [],
        "separator": "",
        "folder": "audio/Ambience/"
    }

    param_config = {
        "Bgm": {
            "validate_type": "Music",
            "match_word": "stop",
            "stop_format": "StopBgm",
            "format": "Bgm",
            "key": "Arg1"
        },

        "Ambience": {
            "validate_type": "Ambience",
            "match_word": "stop",
            "stop_format": "StopAmbience",
            "format": "Ambience",
            "key": "Arg1"
        },

        "Se": {
            "validate_type": "Sound",
            "match_word": "stop",
            "stop_format": "StopSe",
            "format": "Se",
            "key": "Arg1"
        },
        "Volume": {
            "key": "Arg3"
        },
        "AudioFadeTime": {
            "key": "Arg6",
            "default": "2.0"
        },
        "WaitType":{
            "key": "WaitType",
            "translate_type": "WaitType"
        }
    }

    # 音频类型列表（避免每次创建）
    AUDIO_TYPES = ["Bgm", "Se", "Ambience"]

    @property
    def category(self):
        return "Audio"

    @property
    def priority(self) -> int:
        return 100

    def can_process(self, data: Dict[str, Any]) -> bool:
        """
        判断是否可以处理给定的数据
        需要存在除去WaitType以外的任何参数
        Args:
            data: 参数字典

        Returns:
            bool: 是否可以处理
        """
        # 检查是否还有其他参数（除了WaitType）
        data_copy = data.copy()
        data_copy.pop("WaitType", None)
        return bool(data_copy)

    def process(self, data: Dict[str, Any]) -> Optional[list]:
        """
        处理音频参数（性能优化版本）

        Args:
            data: 参数字典

        Returns:
            List[Dict[str, Any]]: 生成的音频命令
        """
        if not self.can_process(data):
            return None

        data = self.do_translate(data)
        lines = []

        for audio_type in self.AUDIO_TYPES:
            if audio_type not in data:
                continue

            audio_value = data[audio_type]
            # 转换为字符串（如果需要）
            if audio_value:
                audio_value = str(audio_value)

            line = {}
            if self.exists_param("WaitType", data):
                self._set_param_fast(line, "WaitType", data)
            # 使用基类的配置缓存
            audio_cfg = self.get_cached_config(audio_type)

            if audio_value == "停止":
                # 停止命令
                line["Command"] = audio_cfg.get("stop_format", "")
                # 自动使用缓存的字段名
                self._set_param_fast(line, "AudioFadeTime", data)
            else:
                # 播放命令
                format_str = audio_cfg.get("format", "")
                if format_str:
                    line["Command"] = format_str.format(value=audio_value) if audio_value else format_str
                else:
                    line["Command"] = audio_type
                
                # 设置音频资源（使用缓存的key）
                audio_key = audio_cfg.get("key", "Arg1")
                line[audio_key] = audio_value
                
                # 设置可选参数（自动使用缓存的字段名）
                self._set_param_fast(line, "Volume", data)
                self._set_param_fast(line, "AudioFadeTime", data)

            lines.append(line)

        return lines
