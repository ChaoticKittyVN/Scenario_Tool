"""
Utage Character & Text Generator
生成文本和对话命令
"""
from typing import Any, Dict, Optional
from core.dict_based_sentence_generator import DictBasedSentenceGenerator
from core.constants import WindowMode, SpecialName


class CharacterTextGenerator(DictBasedSentenceGenerator):
    """角色与文本生成器"""

    # 标记：允许与Macro一起处理（因为Macro可能需要Text）
    ALLOWED_WITH_MACRO = True

    # 资源配置 - 用于资源验证
    resource_config = {
        "resource_type": "Character",
        "resource_category": "图片",
        "main_param": "Character",
        "part_params": ["Varient", "Atr1", "Atr2", "Atr3"],
        "separator": " ",
        "folder": "images/Character/"
    }

    param_config = {
        "CharacterCommand": {
            "translate_type": "CharacterCommand",
        },
        "Character": {
            "translate_type": "Character",
            "key": "Arg1"
        },
        "Varient": {
            "translate_type": "Varient",
            "key": "Arg2"
        },
        "CharacterLayer": {
            "key": "Arg3"
        },
        "Atr1": {},
        "Atr2": {},
        "Atr3": {},
        "CharacterX": {
            "key": "Arg4"
        },
        "CharacterY": {
            "key": "Arg5"
        },
        "CharacterFade": {
            "key": "Arg6",
            "default": "0.5"
        },
        "Name": {
            "translate_type": "Name",
            "key": "Arg1"
        },
        "Text": {
            "key": "Text"
        },
        "Voice": {
            "key": "Voice"
        },
        "MessageWindow":{},
    }

    SPECIAL_NAME_VALUES = {member.value for member in SpecialName}

    @property
    def category(self):
        return "Character&Text"

    @property
    def priority(self) -> int:
        return 900

    def process(self, data: Dict[str, Any]) -> Optional[list]:
        """
        处理文本参数（性能优化版本）

        Args:
            data: 参数字典

        Returns:
            List[Dict[str, Any]]: 生成的角色与文本命令
        """
        if not self.can_process(data):
            return None

        data = self.do_translate(data)

        # 直接获取值并转换为字符串，避免多次方法调用
        character_command = str(data.get("CharacterCommand", "")) if "CharacterCommand" in data else ""
        character_name = str(data.get("Name", "")) if "Name" in data else ""
        character = str(data.get("Character", "")) if "Character" in data else ""
        text = str(data.get("Text", "")) if "Text" in data else ""

        lines = []

        is_off = (character_command == "off")
        same_chara = (character == character_name)

        # 处理角色
        line = {}
        if character and not is_off:
            # 使用缓存的字段名
            character_field = self.get_cached_field("Character", "Arg1")
            line[character_field] = character
            # 自动使用缓存的字段名

            varient = self.get_value("Varient", data)

            line["Arg2"] = varient
            self._set_param_fast(line, "CharacterLayer", data)
            self._set_param_fast(line, "CharacterFade", data, use_default=True)

        elif is_off:
            line["Command"] = "CharacterOff"
            self._set_param_fast(line, "Character", data)
            self._set_param_fast(line, "CharacterLayer", data)
            self._set_param_fast(line, "CharacterFade", data, use_default=True)


        if not same_chara:
            lines.append(line)
            line = {}

        window = str(data.get("MessageWindow", "")) if "MessageWindow" in data else ""
        # 处理窗口显示
        if window in [WindowMode.SHOW.value, WindowMode.SHOW_AND_HIDE.value]:
            lines.append({"Command": "ShowMessageWindow"})

        # 处理对话文本
        if character_name and not same_chara:
            # if character_name in self.SPECIAL_NAME_VALUES:
            #     # elif character_name == SpecialName.LABEL_CAMMAND.value:
            #     #     lines.append(f"label {text}:")
            #     # else:
            #     #     raise ValueError(f"不支持的特殊说话者：{character_name}。")
            # else:
                # character_name = self.translator.translate("Name", character_name)
            line = {}
            if self.exists_param("Voice", data):
                self._set_param_fast(line, "Voice", data)
            # 使用缓存的字段名
            name_field = self.get_cached_field("Name", "Arg2")
            line[name_field] = character_name
            if text:
                text_field = self.get_cached_field("Text", "Text")
                line[text_field] = text
            lines.append(line)
        else:
            if self.exists_param("Voice", data):
                self._set_param_fast(line, "Voice", data)            
            if text:
                text_field = self.get_cached_field("Text", "Text")
                line[text_field] = text
                lines.append(line)

        if window in [WindowMode.HIDE.value, WindowMode.SHOW_AND_HIDE.value]:
            lines.append({"Command": "HideMessageWindow"})

        return lines
