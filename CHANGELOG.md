# 更新日志

本项目按照语义化版本记录主要变更。

## 0.10.0 - 2026-08-07

### 新增

- 支持通过 `processing.multi_project_mode` 和 `projects` 维护多个篇章的参数数据。
- 单项目配置一个项目时，可自动选择 `param_data_<engine>_<project>.xlsx`，并兼容旧的 `param_data_<project>.xlsx`。
- 支持通过 `engines.enabled` 只启用项目实际包含的引擎；缺少未启用引擎目录时不再阻止启动。
- 新增 Agent 差分文档导出，可保留 `variant_data.xlsx` 的自定义描述列，并生成情绪、序号和适用情绪索引。
- 新增 `tools/count_words.py`，可按文件、工作表和角色统计演出文本，并输出 JSON 报告。
- GUI 工具箱动态读取 `tools/` 脚本的 argparse 参数，改善参数类型、可选值、文件选择和执行状态展示。
- GUI 参数页增加普通差分映射与 Agent 差分文档的独立操作。
- GUI 项目配置与本机 Python 路径、窗口尺寸等本机设置分离。

### 调整

- 将 `update_param.py` 拆分为 `core/param_update/` 服务模块，同时保留原先直接执行即完成映射生成和参数表同步的默认流程。
- `update_param.py` 新增映射、参数表、普通差分和 Agent 差分文档的独立 CLI 模式。
- `tools/run_workflow.py` 和 `tools/smart_fill.py` 补充结构化工具元数据及 GUI 友好的参数说明。
- 参数表内容完全一致时跳过保存；缺少参数表时自动创建。
- 改进缺失值、生成器异常和可选引擎的错误处理。

### 修复

- 修复工具页深浅色主题、复选框可见性及参数布局问题。
- 修复旧测试对已调整入口、配置模型和工具名称的引用。
- 修复字数统计中角色与文本行对应、特殊名称筛选及 END/Ignore 范围处理。

### 已知后续项

- Utage 的部分专用处理仍位于通用核心和 Excel writer 中，计划在后续版本下沉到 Utage 引擎包。
- `run_tool.py` 尚未作为正式入口；批量任务使用 `tools/run_workflow.py`。
- 当前轻量 GUI 启动器依赖本机 Python 环境，不作为 0.10.0 发布内容。

## 0.9.2 - 2026-08-06

- 整合 GUI 工具页面、配置保存和参数更新入口。
- 改进工具脚本的动态发现与界面执行能力。

