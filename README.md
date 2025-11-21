# Scenario Tool - 使用手册

视觉小说脚本生成工具，支持从 Excel 表格生成 Ren'Py 和 Naninovel 引擎脚本。

---

## 快速开始

### GUI 模式

```bash
pip install pandas openpyxl pyyaml PySide6
py run_gui.py
```

GUI 提供四个功能标签页：
- **脚本生成**：从 Excel 生成引擎脚本
- **参数映射**：更新参数映射配置
- **资源管理**：验证和同步资源文件（支持干跑模式）
- **默认配置**：修改全局配置

### 命令行模式

#### 1. 安装依赖

```bash
pip install pandas openpyxl pyyaml
```

#### 2. 配置引擎

编辑 `config.yaml`，选择目标引擎：

```yaml
engine:
  engine_type: "renpy"  # 或 "naninovel"
```

#### 3. 准备数据

将 Excel 文件放入 `input/` 目录。

#### 4. 生成脚本

```bash
py generate_scenario.py
```

生成的脚本保存在 `output/` 目录。

---

## 参数映射管理

### 更新参数映射

当需要修改参数映射时，编辑对应引擎的参数文件，然后运行更新脚本：

```bash
py update_param.py
```

**参数文件位置**：
- Ren'Py: `param_config/param_data_renpy.xlsx`
- Naninovel: `param_config/param_data_naninovel.xlsx`

**参数文件格式**：

每个工作表代表一个参数类型，包含两列：
- `ExcelParam`: Excel 中使用的中文参数
- `ScenarioParam`: 引擎脚本中的实际参数

示例（Speaker 工作表）：
```
ExcelParam | ScenarioParam
-----------|---------------
说话人      | the_speaker
```

**工作流程**：
1. 编辑参数文件（Excel）
2. 运行 `py update_param.py`
3. 自动生成 `param_config/param_mappings.py`
4. 重新运行 `py generate_scenario.py` 生成脚本

---

## 配置说明

### 引擎配置

**切换引擎**：只需修改 `engine_type` 即可

```yaml
# Ren'Py 引擎
engine:
  engine_type: "renpy"

# Naninovel 引擎
engine:
  engine_type: "naninovel"
```

**自定义配置**（可选）：

```yaml
engine:
  engine_type: "renpy"
  indent_size: 4              # 缩进大小
  default_transition: "dissolve"  # 默认转场
```

### 路径配置

```yaml
paths:
  input_dir: "./input"        # Excel 输入目录
  output_dir: "./output"      # 脚本输出目录
  param_config_dir: "./param_config"  # 参数映射目录
```

### 处理配置

```yaml
processing:
  ignore_mode: true           # 启用忽略模式
  ignore_words: ["忽略", ""]  # 忽略标记词
  enable_progress_bar: true   # 显示进度条
```

---

## Excel 格式要求

### 必需列

- `Note`: 注释列，必须包含 "END" 标记表示数据结束
- `Ignore`: 忽略标记列（可选）

### 数据列

根据引擎不同，支持的列有所不同：

**Ren'Py**：
- `Speaker`, `Text` - 对话
- `Character`, `Sprite` - 角色立绘
- `Background` - 背景
- `Music`, `Sound`, `Voice` - 音频
- 等等...

**Naninovel**：
- `Speaker`, `Text` - 对话
- `Char` - 角色
- `Background` - 背景
- `Music`, `Sound` - 音频
- 等等...

### 特殊工作表

- `参数表`: 将被跳过，不生成脚本

---

## 资源管理

### 验证资源完整性

检查 Excel 中引用的资源文件是否存在：

```bash
py validate_resources.py
```

**配置项目目录**：

编辑 `validate_resources.py` 中的 `project_dirs`：

```python
project_dirs = {
    "图片": Path("project/images"),
    "音频": Path("project/audio"),
    "视频": Path("project/video"),
}
```

**验证报告**：

报告保存在 `output/validation_reports/` 目录，包含：
- 各类资源的统计信息
- 缺失文件列表
- 总体完成率

### 同步缺失资源

从资源库同步缺失的资源到项目：

```bash
py sync_resources.py
```

**配置资源库目录**：

编辑 `sync_resources.py` 中的 `source_dirs`：

```python
source_dirs = {
    "图片": Path("resource_library/images"),
    "音频": Path("resource_library/audio"),
    "视频": Path("resource_library/video"),
}
```

**工作流程**：
1. 读取验证报告，获取缺失文件列表
2. 在资源库中查找这些文件
3. 显示同步计划（找到的 + 未找到的）
4. 询问用户确认
5. 执行复制（支持干跑模式）

---

## 测试

运行集成测试：

```bash
py test_all.py
```

测试内容：
- 模块导入
- 彩色日志系统
- 配置管理（引擎切换）
- 引擎注册表
- 参数翻译器
- 异常系统
- 常量管理
- 参数映射更新

---

## 项目结构

```
scenario_tool/
├── core/                          # 核心框架
│   ├── logger.py                  # 日志系统
│   ├── exceptions.py              # 异常类
│   ├── constants.py               # 常量定义
│   ├── config_manager.py          # 配置管理
│   ├── engine_registry.py         # 引擎注册表
│   ├── param_translator.py        # 参数翻译器
│   ├── base_sentence_generator.py # 生成器基类
│   ├── sentence_generator_manager.py  # 生成器管理器
│   └── engine_processor.py        # 引擎处理器
├── engines/
│   ├── renpy/                     # Ren'Py 引擎（12个生成器）
│   └── naninovel/                 # Naninovel 引擎（7个生成器）
├── gui/                           # GUI 界面
│   ├── main.py                    # GUI 主程序
│   ├── ui/                        # UI 定义
│   ├── controllers/               # 控制器
│   └── utils/                     # GUI 工具
├── param_config/                  # 参数映射配置
│   ├── param_data_renpy.xlsx      # Ren'Py 参数文件
│   ├── param_data_naninovel.xlsx  # Naninovel 参数文件
│   ├── varient_data.xlsx          # 差分参数文件（可选）
│   ├── param_mappings.py          # 生成的参数映射（自动生成）
│   └── varient_mappings.py        # 生成的差分参数映射（自动生成）
├── input/                         # Excel 输入目录
├── output/                        # 脚本输出目录
├── logs/                          # 日志目录
├── config.yaml                    # 配置文件
├── run_gui.py                     # GUI 启动脚本
├── generate_scenario.py           # 脚本生成工具
├── update_param.py                # 参数映射更新工具
├── validate_resources.py          # 资源验证工具
├── sync_resources.py              # 资源同步工具
├── test_all.py                    # 集成测试
└── README.md                      # 本文件
```

---

## 日志

日志文件保存在 `logs/scenario_tool.log`，包含详细的执行信息。

控制台输出彩色日志：
- DEBUG: 青色
- INFO: 绿色
- WARNING: 黄色
- ERROR: 红色
- CRITICAL: 紫色

---

## 扩展新引擎

要添加新引擎支持：

1. 在 `engines/` 下创建新目录
2. 创建 `__init__.py` 并使用 `@register_engine` 装饰器
3. 创建 `sentence_generators/` 目录
4. 实现各种生成器类

示例：

```python
from core.engine_registry import register_engine
from core.config_manager import EngineConfig
from core.engine_processor import EngineProcessor

@register_engine(
    name="my_engine",
    display_name="My Engine",
    file_extension=".txt",
    config_class=EngineConfig,
    description="My custom engine"
)
def create_my_engine_processor(config, translator):
    processor = EngineProcessor("my_engine", translator, config)
    processor.setup()
    return processor
```

---

## 常见问题

### Q: 如何切换引擎？

A: 只需修改 `config.yaml` 中的 `engine_type`：

```yaml
engine:
  engine_type: "renpy"  # 或 "naninovel"
```

### Q: 生成的脚本在哪里？

A: 在 `output/` 目录中，文件扩展名根据引擎自动确定：
- Ren'Py: `.rpy`
- Naninovel: `.nani`

### Q: 如何查看详细日志？

A: 查看 `logs/scenario_tool.log` 文件。

### Q: 资源验证报告在哪里？

A: 在 `output/validation_reports/` 目录中。

### Q: 如何添加新的参数映射？

A: 编辑对应引擎的参数文件（`param_config/param_data_renpy.xlsx` 或 `param_config/param_data_naninovel.xlsx`），然后运行 `py update_param.py` 自动生成参数映射。

---

## 许可证

与原项目保持一致
