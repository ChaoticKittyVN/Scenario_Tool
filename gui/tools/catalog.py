"""Discover CLI tools without importing or executing their modules."""

from __future__ import annotations

import ast
import shlex
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


def _literal(node: ast.AST | None) -> Any:
    if node is None:
        return None
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        pass
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parts = []
        current: ast.AST = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    if isinstance(node, ast.Call) and node.args:
        function_name = _literal(node.func)
        if function_name in ("Path", "pathlib.Path"):
            return str(_literal(node.args[0]))
    return None


def _split_values(value: str) -> list[str]:
    value = value.strip()
    if not value:
        return []
    if "," in value:
        return [item.strip() for item in value.split(",") if item.strip()]
    return [item.strip("\"'") for item in shlex.split(value, posix=False)]


def _metadata_order(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return fallback


@dataclass(frozen=True)
class ToolArgument:
    flags: tuple[str, ...]
    dest: str
    help: str = ""
    action: str = "store"
    required: bool = False
    default: Any = None
    choices: tuple[Any, ...] = ()
    nargs: str | int | None = None
    type_name: str | None = None
    label: str = ""
    group: str = "常用参数"
    kind: str = "auto"
    placeholder: str = ""
    file_filter: str = ""
    hidden: bool = False
    order: int = 100

    @property
    def option(self) -> str:
        long_flags = [flag for flag in self.flags if flag.startswith("--")]
        if long_flags:
            return max(long_flags, key=len)
        return self.flags[0] if self.flags else self.dest

    @property
    def is_optional(self) -> bool:
        return any(flag.startswith("-") for flag in self.flags)

    @property
    def is_boolean(self) -> bool:
        return self.action in ("store_true", "store_false")

    @property
    def takes_multiple(self) -> bool:
        return self.nargs in ("+", "*") or isinstance(self.nargs, int)

    @property
    def display_label(self) -> str:
        return self.label or self.option

    @property
    def display_type(self) -> str:
        if self.kind == "file":
            return "文件"
        if self.kind == "save_file":
            return "输出文件"
        if self.kind == "directory":
            return "目录"
        if self.is_boolean:
            return "开关"
        if self.choices:
            return "选项"
        if self.takes_multiple or self.action == "append":
            return "多值"
        if self.type_name in ("Path", "pathlib.Path"):
            return "路径"
        return "文本"

    def values_to_argv(self, value: Any) -> list[str]:
        if self.is_boolean:
            return [self.option] if bool(value) else []
        if value is None or value == "":
            return []
        values: list[str]
        if isinstance(value, str):
            values = _split_values(value) if self.takes_multiple or self.action == "append" else [value]
        elif isinstance(value, Iterable):
            values = [str(item) for item in value]
        else:
            values = [str(value)]
        if not values:
            return []
        if self.action == "append":
            result: list[str] = []
            for item in values:
                result.extend([self.option, item])
            return result
        return ([self.option] if self.is_optional else []) + values


@dataclass(frozen=True)
class ToolDescriptor:
    name: str
    script_path: Path
    title: str
    description: str
    arguments: tuple[ToolArgument, ...] = ()
    parse_error: str | None = None

    @property
    def supports_dry_run(self) -> bool:
        return any("--dry-run" in argument.flags for argument in self.arguments)

    @property
    def requires_confirmation(self) -> bool:
        return not self.supports_dry_run

    def build_arguments(
        self,
        values: Mapping[str, Any],
        extra_arguments: Sequence[str] = (),
    ) -> list[str]:
        result: list[str] = []
        for argument in self.arguments:
            result.extend(argument.values_to_argv(values.get(argument.dest)))
        result.extend(str(argument) for argument in extra_arguments if str(argument))
        return result


@dataclass
class ToolCatalog:
    tools_dir: Path
    ignored_names: set[str] = field(default_factory=lambda: {"__init__"})

    def discover(self) -> list[ToolDescriptor]:
        if not self.tools_dir.exists():
            return []
        descriptors = [
            self.read(path)
            for path in sorted(self.tools_dir.glob("*.py"), key=lambda item: item.name.lower())
            if path.stem not in self.ignored_names and not path.name.startswith("_")
        ]
        return sorted(descriptors, key=lambda item: (item.title.lower(), item.name.lower()))

    def read(self, script_path: Path) -> ToolDescriptor:
        try:
            source = script_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(script_path))
            description = (ast.get_docstring(tree) or "").strip()
            ui_metadata = self._read_ui_metadata(tree)
            arguments = self._apply_ui_metadata(
                self._read_arguments(tree),
                ui_metadata.get("arguments", {}),
            )
            title = str(ui_metadata.get("title") or "").strip()
            if not title:
                title = description.splitlines()[0].strip() if description else script_path.stem.replace("_", " ")
            display_description = str(ui_metadata.get("description") or "").strip() or description
            return ToolDescriptor(
                name=script_path.stem,
                script_path=script_path.resolve(),
                title=title,
                description=display_description,
                arguments=tuple(arguments),
            )
        except (OSError, SyntaxError, UnicodeError) as exc:
            return ToolDescriptor(
                name=script_path.stem,
                script_path=script_path.resolve(),
                title=script_path.stem.replace("_", " "),
                description="",
                parse_error=str(exc),
            )

    @staticmethod
    def _read_ui_metadata(tree: ast.Module) -> dict[str, Any]:
        for node in tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if not any(isinstance(target, ast.Name) and target.id == "TOOL_UI" for target in targets):
                continue
            value = _literal(node.value)
            return value if isinstance(value, dict) else {}
        return {}

    @staticmethod
    def _apply_ui_metadata(
        arguments: list[ToolArgument],
        metadata: Any,
    ) -> list[ToolArgument]:
        if not isinstance(metadata, dict):
            return arguments
        result = []
        for index, argument in enumerate(arguments):
            overrides = metadata.get(argument.dest, {})
            if not isinstance(overrides, dict):
                overrides = {}
            result.append(
                replace(
                    argument,
                    label=str(overrides.get("label") or ""),
                    group=str(overrides.get("group") or "常用参数"),
                    kind=str(overrides.get("kind") or "auto"),
                    placeholder=str(overrides.get("placeholder") or ""),
                    file_filter=str(overrides.get("file_filter") or ""),
                    hidden=bool(overrides.get("hidden", False)),
                    order=_metadata_order(overrides.get("order"), index + 100),
                )
            )
        return sorted(result, key=lambda item: item.order)

    @staticmethod
    def _read_arguments(tree: ast.AST) -> list[ToolArgument]:
        arguments: list[ToolArgument] = []
        seen: set[tuple[str, ...]] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != "add_argument":
                continue
            flags = tuple(
                value
                for argument in node.args
                if isinstance((value := _literal(argument)), str)
            )
            if not flags or flags in seen:
                continue
            seen.add(flags)
            keywords = {keyword.arg: _literal(keyword.value) for keyword in node.keywords if keyword.arg}
            dest = keywords.get("dest")
            if not isinstance(dest, str):
                option = max(flags, key=len)
                dest = option.lstrip("-").replace("-", "_")
            choices = keywords.get("choices")
            if not isinstance(choices, (list, tuple)):
                choices = ()
            nargs = keywords.get("nargs")
            if not isinstance(nargs, (str, int)):
                nargs = None
            arguments.append(
                ToolArgument(
                    flags=flags,
                    dest=dest,
                    help=str(keywords.get("help") or ""),
                    action=str(keywords.get("action") or "store"),
                    required=bool(keywords.get("required", False)),
                    default=keywords.get("default"),
                    choices=tuple(choices),
                    nargs=nargs,
                    type_name=(str(keywords["type"]) if keywords.get("type") else None),
                )
            )
        return arguments
