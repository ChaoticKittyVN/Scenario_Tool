"""批量工作流执行器。"""

from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


TOOL_UI = {
    "title": "批量工作流执行器",
    "description": "从 YAML 工作流依次执行多个项目工具，默认使用安全预览模式。",
    "arguments": {
        "workflow": {"label": "工作流文件", "group": "必填参数", "kind": "file", "file_filter": "YAML 文件 (*.yaml *.yml)", "order": 10},
        "dry_run": {"label": "安全预览", "group": "执行模式", "order": 20},
        "apply": {"label": "实际执行", "group": "执行模式", "order": 21},
        "step": {"label": "限定步骤", "group": "执行范围", "placeholder": "每行一个步骤 ID", "order": 30},
        "overrides": {"label": "变量覆盖", "group": "执行范围", "placeholder": "每行一个 NAME=VALUE", "order": 40},
        "report": {"label": "报告文件", "group": "输出", "kind": "save_file", "file_filter": "JSON 文件 (*.json)", "order": 50},
        "no_report": {"label": "不生成报告", "group": "输出", "order": 60},
        "continue_on_error": {"label": "失败后继续", "group": "高级参数", "order": 80},
        "verbose": {"label": "显示完整输出", "group": "高级参数", "order": 81},
        "list_steps": {"label": "仅列出步骤", "group": "高级参数", "order": 82},
        "python": {"hidden": True, "order": 99},
    },
}


class WorkflowError(ValueError):
    """Raised when a workflow definition cannot be executed safely."""


@dataclass
class StepResult:
    step_id: str
    status: str
    target: Optional[str]
    command: List[str]
    cwd: str
    exit_code: Optional[int]
    duration_seconds: float
    stdout: str = ""
    stderr: str = ""
    reason: str = ""


def load_workflow(path: Path) -> Dict[str, Any]:
    """Load and minimally validate a workflow YAML file."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkflowError(f"工作流文件不存在: {path}") from exc
    except yaml.YAMLError as exc:
        raise WorkflowError(f"工作流 YAML 无法解析: {exc}") from exc

    if not isinstance(data, dict):
        raise WorkflowError("工作流根节点必须是对象。")
    if data.get("version", 1) != 1:
        raise WorkflowError(f"不支持的工作流版本: {data.get('version')}")

    steps = data.get("steps")
    if not isinstance(steps, list) or not steps:
        raise WorkflowError("工作流必须包含非空的 steps 列表。")

    seen_ids = set()
    for index, step in enumerate(steps, 1):
        if not isinstance(step, dict):
            raise WorkflowError(f"第 {index} 个步骤必须是对象。")
        step_id = step.get("id")
        if not isinstance(step_id, str) or not step_id.strip():
            raise WorkflowError(f"第 {index} 个步骤缺少有效 id。")
        if step_id in seen_ids:
            raise WorkflowError(f"步骤 id 重复: {step_id}")
        seen_ids.add(step_id)

        entrypoints = [key for key in ("script", "module") if step.get(key)]
        if len(entrypoints) != 1:
            raise WorkflowError(
                f"步骤 {step_id} 必须且只能指定 script 或 module。"
            )
        for key in ("args", "dry_run_args", "apply_args"):
            if key in step and not isinstance(step[key], list):
                raise WorkflowError(f"步骤 {step_id} 的 {key} 必须是列表。")
        if step.get("for_each") not in (None, "targets"):
            raise WorkflowError(f"步骤 {step_id} 的 for_each 目前只支持 targets。")
        if step.get("preview", "auto") not in ("auto", "run", "skip"):
            raise WorkflowError(f"步骤 {step_id} 的 preview 必须是 auto、run 或 skip。")

    return data


def parse_overrides(values: Sequence[str]) -> Dict[str, str]:
    overrides: Dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise WorkflowError(f"变量覆盖必须使用 NAME=VALUE: {value}")
        name, raw_value = value.split("=", 1)
        name = name.strip()
        if not name:
            raise WorkflowError(f"变量名不能为空: {value}")
        overrides[name] = raw_value
    return overrides


def format_text(value: Any, context: Mapping[str, Any], label: str) -> str:
    try:
        return str(value).format_map(context)
    except KeyError as exc:
        raise WorkflowError(f"{label} 引用了未定义变量: {exc.args[0]}") from exc


def format_list(values: Iterable[Any], context: Mapping[str, Any], label: str) -> List[str]:
    return [format_text(value, context, label) for value in values]


def display_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path.resolve())


def expand_targets(
    raw_targets: Sequence[Any],
    context: Mapping[str, Any],
    repo_root: Path,
) -> List[str]:
    targets: List[str] = []
    seen = set()
    for raw_target in raw_targets:
        pattern = format_text(raw_target, context, "targets")
        pattern_path = Path(pattern)
        absolute_pattern = pattern_path if pattern_path.is_absolute() else repo_root / pattern_path
        has_glob = any(char in pattern for char in "*?[")
        matches = [Path(item) for item in glob.glob(str(absolute_pattern), recursive=True)] if has_glob else [absolute_pattern]

        if not matches or (not has_glob and not absolute_pattern.exists()):
            raise WorkflowError(f"目标不存在或未匹配任何文件: {pattern}")

        for match in sorted(matches, key=lambda item: str(item).lower()):
            if not match.exists() or match.name.startswith("~"):
                continue
            rendered = display_path(match, repo_root)
            if rendered not in seen:
                targets.append(rendered)
                seen.add(rendered)
    return targets


class WorkflowRunner:
    """Build and execute workflow steps through the current Python interpreter."""

    def __init__(
        self,
        workflow: Dict[str, Any],
        workflow_path: Path,
        mode: str,
        python_executable: Path,
        repo_root: Path = REPO_ROOT,
        selected_steps: Optional[Sequence[str]] = None,
        variable_overrides: Optional[Mapping[str, str]] = None,
        continue_on_error: bool = False,
        verbose: bool = False,
    ):
        self.workflow = workflow
        self.workflow_path = workflow_path.resolve()
        self.mode = mode
        self.python_executable = python_executable.resolve()
        self.repo_root = repo_root.resolve()
        self.selected_steps = set(selected_steps or [])
        self.variable_overrides = dict(variable_overrides or {})
        self.continue_on_error = continue_on_error
        self.verbose = verbose

        variables = workflow.get("variables", {})
        if not isinstance(variables, dict):
            raise WorkflowError("variables 必须是对象。")
        self.base_context: Dict[str, Any] = {
            key: value for key, value in variables.items()
        }
        self.base_context.update(self.variable_overrides)
        self.base_context.update(
            {
                "repo_root": str(self.repo_root),
                "workflow_dir": str(self.workflow_path.parent),
                "python": str(self.python_executable),
                "mode": self.mode,
            }
        )

        raw_targets = workflow.get("targets", [])
        if not isinstance(raw_targets, list):
            raise WorkflowError("targets 必须是列表。")
        self.targets = expand_targets(raw_targets, self.base_context, self.repo_root)

        available_steps = {step["id"] for step in workflow["steps"]}
        unknown_steps = self.selected_steps - available_steps
        if unknown_steps:
            raise WorkflowError(f"指定了不存在的步骤: {', '.join(sorted(unknown_steps))}")

    def _step_context(self, target: Optional[str]) -> Dict[str, Any]:
        context = dict(self.base_context)
        if target is not None:
            target_path = Path(target)
            context.update(
                {
                    "target": target,
                    "target_name": target_path.name,
                    "target_stem": target_path.stem,
                    "target_dir": str(target_path.parent),
                }
            )
        return context

    def _build_command(
        self,
        step: Mapping[str, Any],
        context: Mapping[str, Any],
    ) -> Tuple[List[str], Path, Optional[str], Dict[str, str]]:
        command = [str(self.python_executable), "-B"]
        if step.get("script"):
            script_value = format_text(step["script"], context, f"步骤 {step['id']} script")
            script_path = Path(script_value)
            if not script_path.is_absolute():
                script_path = self.repo_root / script_path
            if not script_path.is_file():
                raise WorkflowError(f"步骤 {step['id']} 的脚本不存在: {script_path}")
            command.append(str(script_path.resolve()))
        else:
            command.extend(["-m", format_text(step["module"], context, f"步骤 {step['id']} module")])

        command.extend(format_list(step.get("args", []), context, f"步骤 {step['id']} args"))
        if self.mode == "dry-run":
            command.extend(
                format_list(step.get("dry_run_args", []), context, f"步骤 {step['id']} dry_run_args")
            )
        else:
            command.extend(
                format_list(step.get("apply_args", []), context, f"步骤 {step['id']} apply_args")
            )

        cwd_value = format_text(step.get("cwd", self.repo_root), context, f"步骤 {step['id']} cwd")
        cwd = Path(cwd_value)
        if not cwd.is_absolute():
            cwd = self.repo_root / cwd
        if not cwd.is_dir():
            raise WorkflowError(f"步骤 {step['id']} 的工作目录不存在: {cwd}")

        stdin_key = "dry_run_stdin" if self.mode == "dry-run" else "apply_stdin"
        stdin_value = step.get(stdin_key, step.get("stdin"))
        stdin_text = None if stdin_value is None else format_text(stdin_value, context, f"步骤 {step['id']} stdin")

        env = os.environ.copy()
        env.setdefault("PYTHONUTF8", "1")
        env.setdefault("PYTHONUNBUFFERED", "1")
        step_env = step.get("env", {})
        if not isinstance(step_env, dict):
            raise WorkflowError(f"步骤 {step['id']} 的 env 必须是对象。")
        for key, value in step_env.items():
            env[str(key)] = format_text(value, context, f"步骤 {step['id']} env")

        return command, cwd.resolve(), stdin_text, env

    def _should_skip_preview(self, step: Mapping[str, Any]) -> bool:
        if self.mode != "dry-run":
            return False
        preview = step.get("preview", "auto")
        if preview == "skip":
            return True
        if preview == "run":
            return False
        return "dry_run_args" not in step

    def _execution_units(self) -> List[Tuple[Mapping[str, Any], Optional[str]]]:
        units: List[Tuple[Mapping[str, Any], Optional[str]]] = []
        for step in self.workflow["steps"]:
            if self.selected_steps and step["id"] not in self.selected_steps:
                continue
            targets: Sequence[Optional[str]]
            if step.get("for_each") == "targets":
                if not self.targets:
                    raise WorkflowError(f"步骤 {step['id']} 要求 targets，但工作流没有目标。")
                targets = self.targets
            else:
                targets = [None]
            units.extend((step, target) for target in targets)
        return units

    def run(self) -> Dict[str, Any]:
        started_at = datetime.now().astimezone()
        units = self._execution_units()
        results: List[StepResult] = []
        halted = False

        print(f"工作流: {self.workflow.get('name', self.workflow_path.stem)}")
        print(f"模式: {'预览' if self.mode == 'dry-run' else '执行'}")
        print(f"步骤任务数: {len(units)}")

        for index, (step, target) in enumerate(units, 1):
            step_id = step["id"]
            label = f"{step_id} [{target}]" if target else step_id
            if halted:
                results.append(
                    StepResult(step_id, "skipped", target, [], str(self.repo_root), None, 0.0, reason="previous_failure")
                )
                print(f"[{index}/{len(units)}] {label}: 跳过（前序步骤失败）")
                continue
            if step.get("enabled", True) is False:
                results.append(
                    StepResult(step_id, "skipped", target, [], str(self.repo_root), None, 0.0, reason="disabled")
                )
                print(f"[{index}/{len(units)}] {label}: 跳过（已禁用）")
                continue
            if self._should_skip_preview(step):
                results.append(
                    StepResult(step_id, "skipped", target, [], str(self.repo_root), None, 0.0, reason="no_safe_preview")
                )
                print(f"[{index}/{len(units)}] {label}: 跳过（没有安全预览模式）")
                continue

            context = self._step_context(target)
            command, cwd, stdin_text, env = self._build_command(step, context)
            timeout = step.get("timeout")
            if timeout is not None:
                try:
                    timeout = float(timeout)
                except (TypeError, ValueError) as exc:
                    raise WorkflowError(f"步骤 {step_id} 的 timeout 必须是数字。") from exc

            print(f"[{index}/{len(units)}] {label}: 运行")
            started = time.perf_counter()
            try:
                completed = subprocess.run(
                    command,
                    cwd=cwd,
                    env=env,
                    input=stdin_text,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    capture_output=True,
                    timeout=timeout,
                    check=False,
                )
                duration = time.perf_counter() - started
                status = "success" if completed.returncode == 0 else "failed"
                result = StepResult(
                    step_id=step_id,
                    status=status,
                    target=target,
                    command=command,
                    cwd=str(cwd),
                    exit_code=completed.returncode,
                    duration_seconds=round(duration, 3),
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                )
            except subprocess.TimeoutExpired as exc:
                duration = time.perf_counter() - started
                result = StepResult(
                    step_id=step_id,
                    status="failed",
                    target=target,
                    command=command,
                    cwd=str(cwd),
                    exit_code=None,
                    duration_seconds=round(duration, 3),
                    stdout=exc.stdout or "",
                    stderr=exc.stderr or "",
                    reason="timeout",
                )

            results.append(result)
            print(f"[{index}/{len(units)}] {label}: {'成功' if result.status == 'success' else '失败'} ({result.duration_seconds:.3f}s)")
            if self.verbose or result.status == "failed":
                if result.stdout.strip():
                    print(result.stdout.rstrip())
                if result.stderr.strip():
                    print(result.stderr.rstrip(), file=sys.stderr)

            if result.status == "failed" and not (
                self.continue_on_error or step.get("continue_on_error", False)
            ):
                halted = True

        finished_at = datetime.now().astimezone()
        counts = {
            status: sum(1 for result in results if result.status == status)
            for status in ("success", "failed", "skipped")
        }
        status = "failed" if counts["failed"] else "success"
        return {
            "workflow": self.workflow.get("name", self.workflow_path.stem),
            "workflow_file": str(self.workflow_path),
            "mode": self.mode,
            "status": status,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
            "counts": counts,
            "targets": self.targets,
            "results": [asdict(result) for result in results],
        }


def default_report_path(workflow: Mapping[str, Any], repo_root: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    raw_name = str(workflow.get("name", "workflow"))
    safe_name = "".join(char if char.isalnum() or char in "-_" else "-" for char in raw_name).strip("-")
    return repo_root / "logs" / "workflows" / f"{timestamp}-{safe_name or 'workflow'}.json"


def write_report(report: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="从 YAML 批量执行项目中的 Python 工具脚本。默认使用安全预览模式。"
    )
    parser.add_argument("--workflow", "-w", type=Path, required=True, help="工作流 YAML 文件。")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="执行各步骤的安全预览；这是默认模式。")
    mode.add_argument("--apply", action="store_true", help="执行实际工作流，包括写入步骤。")
    parser.add_argument("--step", action="append", default=[], help="只执行指定步骤，可重复使用。")
    parser.add_argument("--set", dest="overrides", action="append", default=[], metavar="NAME=VALUE", help="覆盖 variables 中的值。")
    parser.add_argument("--python", type=Path, default=Path(sys.executable), help="用于运行子工具的 Python。")
    parser.add_argument("--report", type=Path, help="JSON 报告路径；默认写入 logs/workflows。")
    parser.add_argument("--no-report", action="store_true", help="不写 JSON 报告。")
    parser.add_argument("--continue-on-error", action="store_true", help="步骤失败后继续执行后续步骤。")
    parser.add_argument("--verbose", "-v", action="store_true", help="在控制台显示子工具的完整输出。")
    parser.add_argument("--list-steps", action="store_true", help="列出工作流步骤后退出。")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    workflow_path = args.workflow.resolve()
    try:
        workflow = load_workflow(workflow_path)
        if args.list_steps:
            for step in workflow["steps"]:
                state = "enabled" if step.get("enabled", True) else "disabled"
                print(f"{step['id']}\t{state}")
            return 0

        runner = WorkflowRunner(
            workflow=workflow,
            workflow_path=workflow_path,
            mode="apply" if args.apply else "dry-run",
            python_executable=args.python,
            selected_steps=args.step,
            variable_overrides=parse_overrides(args.overrides),
            continue_on_error=args.continue_on_error,
            verbose=args.verbose,
        )
        report = runner.run()
        if not args.no_report:
            report_path = args.report or default_report_path(workflow, REPO_ROOT)
            if not report_path.is_absolute():
                report_path = REPO_ROOT / report_path
            write_report(report, report_path)
            print(f"报告: {report_path.resolve()}")

        counts = report["counts"]
        print(
            "结果: "
            f"成功 {counts['success']}, 失败 {counts['failed']}, 跳过 {counts['skipped']}"
        )
        return 0 if report["status"] == "success" else 1
    except WorkflowError as exc:
        print(f"工作流配置错误: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("工作流已中断。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
