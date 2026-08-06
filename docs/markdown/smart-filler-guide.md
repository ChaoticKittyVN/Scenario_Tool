# 通用表格变更工具

`tools/smart_fill.py` 根据 YAML 配置批量修改演出 Excel。它适合默认值、继承、编号、模板命名、映射、条件清空和列复制等通用劳动；复杂业务仍应保留为专用工具。

执行器先为整个文件生成 `ChangePlan`，确认同一单元格没有冲突后才统一写入。写入使用 `ExcelEditor` 原地修改，不会用 pandas 重建工作簿。

## 直接执行

从仓库根目录执行：

```powershell
$python = "D:\python\python.exe"

# 预览，不写入 Excel
& $python -B tools\smart_fill.py --dry-run

# 正式应用；不带 --dry-run 仍保持历史上的直接写入行为
& $python -B tools\smart_fill.py

# 指定配置、输入目录或工作表
& $python -B tools\smart_fill.py `
  --config config\filling_rules.yaml `
  --input-dir input `
  --sheets "对话,剧本" `
  --dry-run
```

也可以在 VS Code 中直接运行 `tools/smart_fill.py`。脚本会自行定位仓库根目录，不依赖当前工作目录，也不经过尚未完成的 `run_tool.py`。

默认 JSON 报告写入 `logs/table_transform/`。控制台只输出文件级统计；`--verbose` 可显示每个单元格变更，`--no-report` 可禁用报告。

## 配置结构

```yaml
version: 1
conflict_policy: error

operations:
  - id: narrator-default
    op: set_default
    target: [Name, Speaker, 角色]
    value: 旁白
    when:
      nonempty_any: [Text, 台词, 对话]
```

- `id`：操作的稳定标识，会写入变更报告。
- `op`：内置操作名或插件注册名。
- `target`：目标列名；列表表示按顺序尝试列名别名。
- `source`：需要源列的操作使用。
- `when`：行级条件，省略表示所有行。
- `options`：操作专用选项。
- `sheets` / `exclude_sheets`：限制或排除工作表。
- `enabled: false`：临时关闭操作。

`conflict_policy` 控制多个操作修改同一单元格时的行为：

- `error`：停止该文件，不写入任何变更，默认且最安全。
- `first`：保留第一个操作的结果。
- `last`：保留最后一个操作的结果。

## 内置操作

### set_default

只填充空单元格。`options.overwrite: true` 可允许覆盖。

```yaml
- id: volume-default
  op: set_default
  target: [Volume, 音量]
  value: "100"
```

### copy_nearest

从当前行上方或下方最近的非空值继承。`source` 省略时读取目标列本身。

```yaml
- id: inherit-background
  op: copy_nearest
  target: [Background, 场景背景]
  options:
    direction: upward
```

### sequence

为符合条件的行生成序号。

```yaml
- id: fill-index
  op: sequence
  target: Index
  when:
    nonempty: Text
  options:
    start: 1
    step: 1
    clear_invalid: false
```

复杂的 Index 有效行判断仍应使用专用的 `tools/fill_scenario_index.py`。

### template

使用行数据和计数器生成值：

```yaml
- id: generate-voice-id
  op: template
  target: [Voice, voice]
  value: "{speaker}_{counter:03d}.wav"
  when:
    all:
      - nonempty_any: [Name, Speaker, 角色]
      - nonempty_any: [Text, 台词, 对话]
  options:
    counter_scope: file
    counter_by: [speaker]
    variables:
      speaker: [Name, Speaker, 角色]
```

模板可直接引用实际列名，也可引用 `variables` 中定义的别名。内置变量包括 `counter`、`row`、`sheet`、`file` 和 `file_stem`。计数范围支持 `global`、`file`、`sheet`。

### map_value

```yaml
- id: normalize-position
  op: map_value
  source: Position
  target: Position
  mapping:
    左: left
    中: center
    右: right
```

### clear_when

```yaml
- id: clear-voice-on-empty-text
  op: clear_when
  target: Voice
  when:
    empty: Text
```

### copy_column

```yaml
- id: copy-speaker
  op: copy_column
  source: Character
  target: Name
```

默认只写入空目标；使用 `options.overwrite: true` 可覆盖。

## 条件

条件支持 `all`、`any` 组合，以及：

```yaml
when:
  all:
    - nonempty_any: [Text, 台词]
    - empty: Voice
    - not_in:
        Name: [label, jump]
```

可用字段为 `empty`、`nonempty`、`empty_any`、`nonempty_any`、`equals`、`not_equals`、`in`、`not_in`。缺少条件引用的列时，该条件不匹配，而不是隐式修改数据。

## 项目级插件

无法用内置操作表达、但仍适合共享执行流程的逻辑，可以实现 `TableOperation`：

```python
from core.table_transform import TableOperation


class ProjectOperation(TableOperation):
    operation_type = "project_operation"

    def plan(self, context):
        return []
```

配置中加载插件类：

```yaml
plugins:
  - project_operations.module:ProjectOperation

operations:
  - id: project-rule
    op: project_operation
    target: SomeColumn
```

插件只负责根据 `OperationContext` 返回 `CellChange`，不要自行保存 Excel。这样 CLI、批量工作流和未来 GUI 可以复用相同的预览、冲突检查、报告与写入过程。

## 与专用工具的边界

- 通用的“条件 + 单元格变换”放入 `core/table_transform` 或 YAML。
- 具有复杂定位、跨文件同步、特殊确认流程的功能继续使用 `tools/` 专用脚本。
- 专用工具中稳定且可复用的局部规则，可以逐步提取成 `TableOperation`，不要求一次性迁移。
- `update_param.py` 继续负责从 `param_data` 同步参数映射和输入表格中的参数表，smart_fill 不替代这条流程。

批量串联请使用 `tools/run_workflow.py`，不要使用尚未完成的 `run_tool.py`。
