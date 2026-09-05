"""Shared helpers for LetsGal code generators."""

import json
from typing import Any, Iterable, Optional

from core.base_sentence_generator import BaseSentenceGenerator


class LetsGalGeneratorBase(BaseSentenceGenerator):
    """Small normalization layer shared by code generators.

    Spreadsheet cells stay semantic and human-readable. The helpers only
    normalize values at the final code-generation boundary.
    """

    @staticmethod
    def is_empty(value: Any) -> bool:
        if value is None or value == "":
            return True
        try:
            return bool(value != value)
        except (TypeError, ValueError):
            return False

    @classmethod
    def first_value(
        cls,
        data: dict,
        names: Iterable[str],
        default: Any = None,
    ) -> Any:
        for name in names:
            value = data.get(name)
            if not cls.is_empty(value):
                return value
        return default

    @classmethod
    def normalize_bool(cls, value: Any, *, default: Optional[bool] = None) -> Optional[bool]:
        if cls.is_empty(value):
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        normalized = str(value).strip().lower()
        if normalized in {"true", "1", "yes", "y", "on", "是", "显示", "开启", "循环"}:
            return True
        if normalized in {"false", "0", "no", "n", "off", "否", "隐藏", "关闭", "不循环"}:
            return False
        raise ValueError(f"无法解析 LetsGal 布尔值: {value!r}")

    @staticmethod
    def quote_text(value: Any) -> str:
        """Quote dialogue text using the code layer's double-quoted form."""
        return json.dumps(str(value), ensure_ascii=False)

    @classmethod
    def normalize_position(cls, value: Any) -> str:
        if cls.is_empty(value):
            return ""
        aliases = {
            "左": "left",
            "中": "center",
            "中央": "center",
            "右": "right",
        }
        return aliases.get(str(value).strip(), str(value).strip())

    @classmethod
    def normalize_transition(cls, value: Any) -> str:
        if cls.is_empty(value):
            return ""
        aliases = {
            "无": "",
            "空": "",
            "empty": "",
            "none": "",
            "渐变": "fade",
            "淡入淡出": "fade",
            "溶解": "dissolve",
        }
        return aliases.get(str(value).strip(), str(value).strip())

    @classmethod
    def normalize_number(cls, value: Any, *, field: str) -> str:
        if cls.is_empty(value):
            return ""
        text = str(value).strip()
        try:
            number = float(text)
        except ValueError as exc:
            raise ValueError(f"{field} 必须是数字或带单位的代码值: {value!r}") from exc
        if number < 0:
            raise ValueError(f"{field} 不能是负数: {value!r}")
        return str(int(number)) if number.is_integer() else str(number)

    @classmethod
    def percent(cls, value: Any) -> str:
        if cls.is_empty(value):
            return ""
        text = str(value).strip()
        return text if text.endswith("%") else f"{text}%"
