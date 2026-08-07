# Tools 工具脚本使用说明

## 概述

`tools/` 目录包含辅助工具脚本。当前直接执行具体脚本；需要串联多个工具时使用 `tools/run_workflow.py`。`run_tool.py` 仍处于规划阶段，不作为可用入口。

## 📖 使用方法

### GUI 工具箱

运行 `python run_gui.py` 后打开“工具箱”标签页。页面会扫描 `tools/*.py`，从源码中读取模块说明和 `argparse.add_argument`，动态生成参数控件；新增标准 argparse 工具时不需要再修改主窗口代码。

- 工具在独立 Python 子进程中执行，工作目录固定为仓库根目录。
- 支持实时输出、交互输入和停止进程。
- 声明 `--dry-run` 的工具默认启用预览模式。
- 取消预览或执行没有 dry-run 的工具前，窗口会再次确认。
- 无法自动表达的参数可放在“附加参数”中，每行作为一个独立参数传递。

工具箱默认使用启动 GUI 的 Python。可在“默认配置”页的“本机 GUI 设置”中选择其他 Python；该路径和窗口尺寸通过 Qt 本机设置保存，不写入、也不会覆盖项目的 `config.yaml`。

“保存项目配置”只更新 GUI 当前管理的项目字段，并保留 `config.yaml` 中其他工具或新版功能添加的未知字段。切换引擎时会重建引擎配置段，避免旧引擎专属字段污染新引擎配置。

### 直接执行

```bash
# 在根目录或 VS Code 中直接运行 tools 中的脚本
python tools/voice_only_script_generate.py

# 或者使用 python -m
python -m tools.voice_only_script_generate
```

**优势：**
- ✅ 便于调试和开发
- ✅ 可以直接传递参数
- ✅ 适合快速测试

## 字数统计工具

`tools/count_words.py` 直接读取指定演出表格，使用与脚本生成相同的 `END` 和 Ignore 规则，并按文件、工作表、角色输出明细。统计时始终保持 `Name` 和 `Text` 的原始行对应关系。GUI 工具箱中可通过文件选择器指定表格。

```powershell
# 直接统计一个表格
python tools/count_words.py --input input/chapter01.xlsx

# 统计指定工作表
python tools/count_words.py --input input/chapter01.xlsx --sheet Scene01 --sheet Scene02

# 排除角色，或只看部分角色
python tools/count_words.py --input input/chapter01.xlsx --exclude-name 系统
python tools/count_words.py --input input/chapter01.xlsx --only-name 主角 --only-name 女主角

# 特殊名称默认不计；按需纳入部分或全部特殊名称
python tools/count_words.py --input input/chapter01.xlsx --include-special-name text
python tools/count_words.py --input input/chapter01.xlsx --include-all-special-names

# 查看可用特殊名称
python tools/count_words.py --list-special-names

# 批量统计目录；完全省略输入时仍使用 config.yaml 的 input_dir
python tools/count_words.py --input-dir input/chapter02
python tools/count_words.py

# 同时保存便于比较的 JSON 报告
python tools/count_words.py --output output/word_count.json

# 审查 END 后或 Ignore 行中是否存在额外文本
python tools/count_words.py --all-rows
```

默认行范围与正式生成一致；`--all-rows` 仅用于排查表尾残留或忽略行，不代表正式脚本字数。特殊名称来自 `core.constants.SpecialName`，默认排除；`--exclude-name` 的优先级高于其他名称选项。

---

## 🎙️ 配音台本导出工具

### 基本用法

```bash
# 导出所有文件的配音台本
python tools/export_dubbing_script.py

# 合并所有文件为一个表格
python tools/export_dubbing_script.py --merge

# 按角色分别导出
python tools/export_dubbing_script.py --per-character

# 指定排序字段
python tools/export_dubbing_script.py --sort 角色 行号

# 输出为 CSV 格式
python tools/export_dubbing_script.py --format csv
```

### 🔄 转换为演出脚本格式

**场景：** 将导出的配音台本转换回演出脚本生成器可识别的格式

```bash
# 基本转换（添加语音文件名和行号前缀）
python tools/export_dubbing_script.py --convert dialogue_主角.xlsx

# 只添加行号，不添加语音文件名
python tools/export_dubbing_script.py --convert dialogue_主角.xlsx --no-voice-prefix

# 不添加任何前缀，只转换列名
python tools/export_dubbing_script.py --convert dialogue_主角.xlsx --no-voice-prefix --no-index

# 批量转换多个文件
for file in dialogue_*.xlsx; do
    python tools/export_dubbing_script.py --convert "$file"
done
```

**转换效果对比：**

| 配音台本列 | → | 演出脚本列 | 说明 |
|-----------|---|-----------|------|
| 角色 | → | Name | 角色名 |
| 文本 | → | Text | 文本内容（可添加前缀） |
| 语音文件名 | → | Voice | 语音文件名 |
| 文本行号 | → | Index | 原始行号（可选） |

**文本前缀格式：**
```
默认：[语音文件名][行号] 原文本
例如：[hero_Sheet1_001][1001] 你好，世界！

无行号：[语音文件名] 原文本
例如：[hero_Sheet1_001] 你好，世界！

无前缀：原文本
例如：你好，世界！
```

### 完整示例流程

```bash
# 1. 从 Excel 剧本导出配音台本
python tools/export_dubbing_script.py --per-character --format excel

# 2. 录音师完成配音后，将生成的配音台本转换回演出脚本格式
python tools/export_dubbing_script.py --convert dialogue_主角.xlsx

# 3. 使用转换后的文件生成演出脚本
# （需要配置 config.yaml 指向正确的输入目录）
python generate_scenario.py
```

---

## 🔧 工具开发模板

如果你要添加新工具，可以参考以下模板：

```python
"""
工具名称描述
"""
import sys
from pathlib import Path

# 支持独立执行
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from core.config_manager import AppConfig
from core.logger import get_logger

logger = get_logger()


def main():
    """主函数（必需）"""
    # 1. 加载配置
    config = AppConfig.from_file("config.yaml")

    # 2. 实现工具逻辑
    logger.info("开始处理...")

    # 3. 输出结果
    logger.info("处理完成")


if __name__ == "__main__":
    main()
```

---

## 批量工作流

工作流执行器位于 `tools/run_workflow.py`。它会自行定位仓库根目录，因此可以直接运行，不依赖 `run_tool.py`：

```powershell
# 默认即安全预览
python tools/run_workflow.py --workflow config/workflows/prepare_and_generate.yaml

# 正式执行
python tools/run_workflow.py --workflow config/workflows/prepare_and_generate.yaml --apply

# 只运行部分步骤
python tools/run_workflow.py --workflow config/workflows/prepare_and_generate.yaml `
  --dry-run --step fill-index --step smart-fill

# 临时覆盖 YAML 变量
python tools/run_workflow.py --workflow config/workflows/prepare_and_generate.yaml `
  --dry-run --set input_dir=input/chapter01
```

默认报告写入 `logs/workflows/`。控制台只显示步骤状态；使用 `--verbose` 查看子工具完整输出。

每个步骤必须指定一个 Python 入口：

```yaml
steps:
  - id: update-parameter-sheet
    script: update_param.py
    args: [--parameter-sheet-only]
    dry_run_args: [--dry-run]
    apply_args: [--apply]

  - id: smart-fill
    module: tools.smart_fill
    args: [--config, "{filling_rules}", --input-dir, "{input_dir}"]
    dry_run_args: [--dry-run]
```

- 预览模式下，有 `dry_run_args` 的步骤会执行安全预览。
- `preview: run` 可将只读步骤直接纳入预览。
- `preview: skip` 会在预览时跳过步骤。
- `apply_args` 可在正式执行时附加 `--yes` 等非交互参数；`apply_stdin` 可兼容仍只有确认提示的旧工具。
- `continue_on_error: true` 可允许单个步骤失败后继续。
- 顶层 `targets` 配合步骤的 `for_each: targets`，可对 glob 匹配的文件逐个执行，并使用 `{target}`、`{target_name}` 等变量。

---

## ❓ 常见问题

### Q: 移入 tools 后还能在 VS Code 直接运行吗？

A: 可以。工具入口会根据 `__file__` 将仓库根目录加入模块搜索路径，不依赖 VS Code 当前工作目录。

### Q: 配音台本的列名可以自定义吗？

A: 目前固定为：角色、文本、语音文件名、文本行号。如需自定义，请修改 `convert_to_performance_format()` 方法中的列名映射。

### Q: 如何批量转换所有配音台本？

A: 使用循环命令：
```bash
# Windows PowerShell
Get-ChildItem dialogue_*.xlsx | ForEach-Object {
    python tools/export_dubbing_script.py --convert $_.Name
}

# Linux/Mac
for file in dialogue_*.xlsx; do
    python tools/export_dubbing_script.py --convert "$file"
done
```
