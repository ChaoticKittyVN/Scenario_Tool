# 配置说明

Scenario Tool 的项目配置位于仓库根目录 `config.yaml`。路径默认相对于仓库根目录解析。

GUI 的工具执行 Python、窗口尺寸等本机设置由 Qt 单独保存，不写入 `config.yaml`。点击“保存项目配置”时，GUI 只更新自己管理的字段，并保留其他已存在配置。

## 引擎配置

`engine.engine_type` 选择当前生成使用的引擎：

```yaml
engine:
  engine_type: renpy  # renpy、naninovel 或 utage
```

`engines.enabled` 是可选引擎白名单：

```yaml
engines:
  enabled:
    - renpy
```

- 空列表表示使用 `engines/` 中实际存在的全部引擎。
- 非空列表只展示并加载指定且实际存在的引擎。
- 项目可以删除不需要的引擎目录，但 `engine.engine_type` 必须指向仍存在且已启用的引擎。

引擎专属字段仍写在 `engine` 下，例如缩进、扩展名或转场默认值。切换引擎时，GUI 会重建该段，避免旧引擎字段残留。

## 路径配置

```yaml
paths:
  input_dir: input
  output_dir: output
  param_config_dir: param_config
  log_dir: logs
  input_voice_dir: input/voice
```

| 字段 | 用途 |
|------|------|
| `input_dir` | 演出 Excel 输入目录 |
| `output_dir` | 生成脚本和报告输出目录 |
| `param_config_dir` | `param_data`、`variant_data` 和生成映射所在目录 |
| `log_dir` | 日志目录 |
| `input_voice_dir` | 语音输入目录 |

建议使用相对路径，便于项目整体移动。

## 处理配置

```yaml
processing:
  batch_size: 100
  enable_progress_bar: true
  ignore_mode: false
  ignore_words:
    - 忽略
    - ""
  multi_project_mode: false
```

- `batch_size`：批处理大小。
- `enable_progress_bar`：命令行是否显示进度条。
- `ignore_mode`：是否按照 `Ignore` 列过滤行。
- `ignore_words`：触发忽略的内容。
- `multi_project_mode`：是否按演出表文件名为不同篇章合并专用参数。

## 项目与篇章参数

`projects` 的键是项目或篇章标识，值是用于匹配演出表文件名的文本：

```yaml
projects:
  chapter_a: 第一篇
  chapter_b: 第二篇
```

### 单项目模式

当 `multi_project_mode: false` 且 `projects` 只有一个有效项目时，基础参数文件按以下顺序选择：

1. `param_data_<engine>_<project>.xlsx`
2. `param_data_<project>.xlsx`，用于兼容旧项目
3. `param_data_<engine>.xlsx`

例如当前引擎为 Ren'Py、项目键为 `chapter_a`，优先读取 `param_data_renpy_chapter_a.xlsx`。

### 多项目模式

当 `multi_project_mode: true` 时：

- 基础参数仍来自 `param_data_<engine>.xlsx`。
- 每个项目使用 `param_data_<project>.xlsx`。
- `update_param.py` 根据 `projects` 的识别文本匹配演出表文件名，再把对应项目参数合并到该工作簿的参数表。
- 文件名匹配不到项目时只使用基础参数；匹配到多个项目时记录警告并使用第一个。

## Agent 差分文档

`variant_agent_export` 控制从 `variant_data.xlsx` 导出的 Agent 专用 JSON：

```yaml
variant_agent_export:
  enabled: false
  output_file: variant_agent_data.json
  group_columns:
    - 情绪
  item_key_column: 序号
  alias_columns:
    - 适用情绪
  parameter_template: "{情绪}{序号}"
  sheet_profiles: {}
```

- `enabled`：完整执行 `update_param.py` 时是否附带生成 Agent 文档。
- `output_file`：输出文件；相对路径以 `param_config_dir` 为基准。
- `group_columns`：建立选择目录的分组列，可配置多个层级。
- `item_key_column`：组内用于列举差分的键。
- `alias_columns`：额外适用情绪或别名列，支持逗号、顿号、竖线和分号分隔。
- `parameter_template`：当 `ScenarioParam` 为空时用于拼接参数；引用列不存在或值为空会中止导出。
- `sheet_profiles`：使用 `"*"` 设置所有工作表，或按工作表名覆盖上述字段。

Agent 文档保留除 `ExcelParam`、`ScenarioParam` 外的全部自定义列，并输出 `selection_index`、`applicability_index` 和逐表警告。

无论 `enabled` 是否开启，都可以单独执行：

```bash
python update_param.py --agent-variant-doc-only
```

## 资源配置

```yaml
resources:
  project_root: project
  source_root: resource_library
  validate_source: true
  filename_normalization:
    音频: [spaces_to_underscores]
  extensions:
    图片: [.png, .jpg, .jpeg, .webp]
    音频: [.ogg, .mp3, .wav, .m4a]
    视频: [.mp4, .webm, .ogv]
```

`project_root` 是引擎项目资源目录，`source_root` 是待同步资源库。没有独立资源库时可将 `validate_source` 设为 `false`，报告只统计项目库。

`filename_normalization` 按资源类别声明文件名查找规则；`spaces_to_underscores` 会在直接查找失败后尝试将空格替换为下划线。`extensions` 按类别声明允许识别的扩展名。

Naninovel 项目可在引擎配置中声明 prefab 成员的控制器文件：

```yaml
engine:
  engine_type: naninovel
  declaration_files:
    Character:
      Hero: declarations/hero.txt
```

该配置由 Naninovel 注册的资源解析器处理，不属于通用资源验证逻辑。

## 演出表要求

常规工作表通常包含：

| 列名 | 说明 |
|------|------|
| `Note` | 注释和流程标记；`END` 表示有效数据结束 |
| `Ignore` | 可选忽略标记 |
| `Name` | 说话人或特殊命令类型 |
| `Text` | 文本内容 |
| `Index` | 稳定行标识，用于导出和同步 |

其他演出列由当前引擎的生成器 `param_config` 决定。工作表中的“参数表”由 `update_param.py` 维护，不参与脚本生成；缺少时会创建，内容完全一致时跳过保存。

## 相关文档

- [参数映射](param-mapping.md)
- [快速开始](getting-started.md)
- [工具脚本](../../TOOLS_README.md)
- [常见问题](faq.md)
