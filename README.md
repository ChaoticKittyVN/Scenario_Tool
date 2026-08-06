# Scenario Tool 0.9.2

视觉小说脚本生成工具，支持从 Excel 表格生成 Ren'Py、Naninovel 和 Utage 引擎脚本。

---

## ✨ 核心特性

- 🎮 **多引擎支持** - 支持 Ren'Py、Naninovel 和 Utage 引擎
- 📊 **Excel 驱动** - 使用熟悉的 Excel 编写脚本
- 🎨 **GUI 界面** - 提供友好的图形界面
- 🔧 **参数映射** - 灵活的参数翻译系统
- 📦 **资源管理** - 自动验证和同步资源文件
- ⚠️ **类型安全** - 避免类型错误
- 🔨 **模块化架构** - 按核心处理、引擎实现和辅助工具拆分，便于扩展与维护

---

## 🚀 快速开始

### 安装python

推荐使用 [Python 3.10.2](https://www.python.org/downloads/) 或更高版本。

### 安装依赖

```bash
pip install -r requirements.txt
```

### 安装依赖（使用清华源）

```bash
pip install -r requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
```

### GUI 模式

```bash
py run_gui.py
```

### 命令行模式

```bash
# 1. 配置引擎（编辑 config.yaml）
# 2. 将 Excel 文件放入 input/ 目录
# 3. 生成脚本
py generate_scenario.py
```

生成的脚本保存在 `output/` 目录。

---

## 📚 文档

### 用户文档

- [快速开始](docs/markdown/getting-started.md) - 安装和基本使用
- [配置说明](docs/markdown/configuration.md) - 引擎配置和路径设置
- [参数映射](docs/markdown/param-mapping.md) - 参数映射管理
- [资源管理](docs/markdown/resource-management.md) - 资源验证和同步
- [常见问题](docs/markdown/faq.md) - 常见问题解答

### 开发文档

- [测试指南](docs/markdown/testing.md) - 运行和编写测试
- [开发指南](docs/markdown/development.md) - 贡献代码和开发环境
- [架构设计](docs/markdown/architecture.md) - 项目架构和设计理念

---

## 🏗️ 项目结构

```
scenario_tool/
├── core/           # 核心框架
│   └── excel_management       # Excel表格操作类
├── engines/        # 引擎实现（Ren'Py、Naninovel、Utage）
├── gui/            # GUI 界面
├── tests/          # 测试代码
├── docs/           # 文档
├── param_config/   # 参数映射配置
├── input/          # Excel 输入目录
└── output/         # 脚本输出目录
```

---

## ⌨️ 常规工作流程

```mermaid
graph LR
    A[在input文件夹中放入需要的演出表格] --> B
    B[更新参数配置表格：编辑param_config中的param_data_引擎类型] --> C
    C[执行update_param] --> D
    D[在演出表格中确认数据验证后进行演出参数填写] --> E
    E[执行generate_scenario] --> F
    F[从output文件夹中获取需要的脚本文件]
```

---

## 🧰 附加功能

除基础的演出脚本生成外，项目还提供以下可直接执行的 Python 工具。所有命令均应在项目根目录运行。

### 自动整理 Index

按照有效文本行预览并重新填写连续的 `Index` 序号：

```bash
# 先预览，不修改文件
python fill_scenario_index.py --input ./input --dry-run

# 确认预览结果后正式执行
python fill_scenario_index.py --input ./input
```

正式执行会原地修改 Excel 文件。当前脚本不支持 `--run` 参数。

### 智能参数填充

根据 YAML 规则填充默认值、继承上下文或生成规则化参数：

```bash
# 使用模块入口，并先进行干跑预览
python -m tools.smart_fill --config ./config/filling_rules.yaml --input-dir ./input --dry-run
```

正式执行前应先确认规则文件可以被 YAML 正确解析，并检查干跑结果。

### 配音、翻译与审查导出

```bash
# 导出配音台本；当前版本建议显式指定实际列名进行排序
python export_dubbing_script.py --sort Name Idx

# 合并导出翻译表格
python export_translation_script.py --merge

# 导出供人工或 AI 审查的纯文本
python export_script_review.py
```

默认输出目录分别为：

- `output/dialogue_exports/`
- `output/translation_exports/`
- `output/script_review/`

### 文本与语音改动同步

将审查表格中的文本或语音文件名回写到原始演出表格：

```bash
# 文本改动预览
python sync_changes.py --input ./input --changes ./input/sync/review.xlsx --dry-run

# 语音改动预览
python sync_voice_changes.py --input ./input --changes ./input/sync/voice.xlsx --dry-run
```

同步工具正式运行时会原地修改 Excel 文件。导出表用于同步前，需要将定位列整理为 `ExcelFilename`、`SheetName` 和 `Index`。

### 资源验证与同步

```bash
# 检查演出表格引用的资源是否存在
python validate_resources.py

# 根据验证报告同步缺失资源
python sync_resources.py
```

验证报告保存在 `output/validation_reports/`。资源同步为交互式操作，建议先选择干跑模式预览复制计划。

### 语音测试脚本生成

从配音台本生成仅包含语音相关内容的测试脚本：

```bash
python -m tools.voice_only_script_generate --input ./input/voice --output ./output/voice_test
```

配音台本通常需要包含 `Name`、`Text`、`Voice` 和 `Index` 列。

---

## 📝 反馈与已知限制

使用过程中可以重点反馈：

- 工具上手难度
- 工具使用的效率提升
- 需要优化的不便之处

**反馈方式**：
1. 前往issues页面提出反馈
2. 描述问题出现的情况
3. 提供示例文件（如可能）
4. 截图错误信息

**已知限制**：
- 不支持Excel合并单元格
- 暂不支持.xlsm格式（宏文件）
- 工作表名称不能包含特殊字符 `: \ / ? * [ ]`

---

## 🤝 贡献

欢迎贡献！请查看 [开发指南](docs/markdown/development.md) 了解如何参与项目。

### 开发环境设置

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
pytest tests/ -v
```

---

## 🔒 安全说明

本工具仅处理本地文件，不会上传任何数据到网络。所有配置和脚本数据都保存在本地。

---

## 📄 许可证

使用 Apache 2.0 License

---

## 🔗 相关链接

- [快速开始指南](docs/markdown/getting-started.md) - 5 分钟上手
- [完整文档](docs/markdown/) - 查看所有文档
- [常见问题](docs/markdown/faq.md) - 遇到问题？先看这里

---

## 🔧 反馈与建议

请前往GitHub的 [issues页面](https://github.com/ChaoticKittyVN/Scenario_Tool/issues) 进行反馈。

反馈建议内容包括BUG、新的引擎支持（需要确认是否普遍使用）、其他功能。
**对于个别引擎的、基于项目要求而产生的对参数以及参数生成逻辑的需求等，不包含在该部分收集的反馈中。**

---

## 🐱 开发者的话

感谢您的支持与使用！


本工具的基础版本在生成演出的功能上采用了固定的模式。
如果您是第一次接触Python或者没有代码经验，在需要自定义生成演出的参数与逻辑的情况下，可能会遇到困难。


推荐您与有程序经验的开发者进行合作，或者联系我们提供基本的帮助。


在使用了本工具的情况下，您发布的游戏中，仅以我个人希望：
- 在工作人员名单中或其他可见位置展示本工作室的logo，并注明使用了本工具。
- 在本工作室合作参与开发的情况，游戏启动画面或其他重要的展示开发者的画面中，展示本工作室的logo。
  
**以上仅作为建议，并非强制要求。**

---

**最后更新**: 2026-08-05
