# 开发指南

本文档介绍如何为 Scenario Tool 贡献代码。

## 开发环境设置

### 1. 克隆仓库

```bash
git clone <repository-url>
cd scenario_tool
```

### 2. 安装依赖

```bash
# 安装生产依赖
pip install -r requirements.txt

# 安装开发依赖
pip install -r requirements-dev.txt
```

### 3. 验证安装

```bash
# 运行集成测试
py _test_all.py

# 运行单元测试
pytest tests/ -v
```

---

## 项目结构

```
scenario_tool/
├── core/                          # 核心框架
│   ├── excel_management/          # Excel表格处理
│   │   ├── __init__.py
│   │   ├── dataframe_processor.py # DataFrame处理
│   │   ├── excel_decorators.py    # 装饰器
│   │   ├── excel_exceptions.py    # Excel异常类
│   │   ├── excel_file_manager.py  # Excel文件管理器
│   │   └── excel_editor.py        # Excel编辑器
│   ├── logger.py                  # 日志系统
│   ├── exceptions.py              # 异常类
│   ├── constants.py               # 常量定义
│   ├── config_manager.py          # 配置管理
│   ├── engine_registry.py         # 引擎注册表
│   ├── param_translator.py        # 参数翻译器
│   ├── base_sentence_generator.py # 生成器基类
│   ├── sentence_generator_manager.py  # 生成器管理器
│   └── engine_processor.py        # 引擎处理器
├── engines/                       # 引擎实现
│   ├── renpy/                     # Ren'Py 引擎
│   │   ├── __init__.py
│   │   └── sentence_generators/   # 句子生成器
│   └── naninovel/                 # Naninovel 引擎
│       ├── __init__.py
│       └── sentence_generators/
├── gui/                           # GUI 界面
│   ├── main.py                    # GUI 主程序
│   ├── ui/                        # UI 定义
│   ├── controllers/               # 控制器
│   └── utils/                     # GUI 工具
├── tests/                         # 测试代码
│   ├── core/                      # 核心模块测试
│   ├── engines/                   # 引擎测试
│   └── gui/                       # GUI 测试
├── docs/                          # 文档
├── param_config/                  # 参数映射配置
├── input/                         # Excel 输入目录
├── output/                        # 脚本输出目录
├── logs/                          # 日志目录
├── config.yaml                    # 配置文件
├── generate_scenario.py           # 脚本生成工具
├── update_param.py                # 参数映射更新工具
├── validate_resources.py          # 资源验证工具
├── sync_resources.py              # 资源同步工具
├── _test_all.py                   # 集成测试
├── requirements.txt               # 生产依赖
├── requirements-dev.txt           # 开发依赖
└── README.md                      # 项目说明
```

---

## 开发工作流

### 1. 创建功能分支

```bash
git checkout -b feature/your-feature-name
```

### 2. 编写代码

遵循项目的代码风格和架构设计。

### 3. 编写测试

为新功能编写单元测试：

```python
# tests/core/test_your_feature.py
import pytest

class TestYourFeature:
    def test_basic_functionality(self):
        # 测试代码
        assert True
```

### 4. 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/core/test_your_feature.py -v

# 检查覆盖率
pytest --cov=. --cov-report=term-missing
```

### 5. 提交代码

```bash
git add .
git commit -m "feat: add your feature description"
```

### 7. 推送并创建 Pull Request

```bash
git push origin feature/your-feature-name
```

---

## 代码规范

### Python 代码风格

遵循 PEP 8 规范：

```python
# ✅ 好的做法
def calculate_total(items: List[Item]) -> float:
    """
    计算总价

    Args:
        items: 商品列表

    Returns:
        float: 总价
    """
    return sum(item.price for item in items)

# ❌ 不好的做法
def calc(i):
    return sum(x.p for x in i)
```

### 命名规范

- **类名**: 使用 PascalCase
  ```python
  class ParamTranslator:
      pass
  ```

- **函数名**: 使用 snake_case
  ```python
  def translate_param(value: str) -> str:
      pass
  ```

- **常量**: 使用 UPPER_SNAKE_CASE
  ```python
  DEFAULT_INDENT_SIZE = 4
  ```

- **私有成员**: 使用单下划线前缀
  ```python
  def _internal_method(self):
      pass
  ```

### 文档字符串

使用 Google 风格的文档字符串：

```python
def process_data(data: Dict[str, Any], config: Config) -> List[str]:
    """
    处理数据并生成结果

    Args:
        data: 输入数据字典
        config: 配置对象

    Returns:
        List[str]: 处理结果列表

    Raises:
        ValueError: 当数据格式不正确时

    Example:
        >>> process_data({"key": "value"}, config)
        ["result1", "result2"]
    """
    pass
```

### 类型注解

使用类型注解提高代码可读性：

```python
from typing import List, Dict, Optional

def translate(
    param_type: str,
    param_value: str,
    default: Optional[str] = None
) -> str:
    """翻译参数"""
    pass
```

---

## 添加新引擎

### 1. 创建引擎目录

```bash
mkdir -p engines/your_engine/sentence_generators
```

### 2. 创建引擎注册

```python
# engines/your_engine/__init__.py
from core.engine_registry import register_engine
from core.config_manager import EngineConfig
from core.engine_processor import EngineProcessor

@register_engine(
    name="your_engine",
    display_name="Your Engine",
    file_extension=".ext",
    config_class=EngineConfig,
    description="Your engine description"
)
def create_your_engine_processor(config, translator):
    """创建引擎处理器"""
    processor = EngineProcessor("your_engine", translator, config)
    processor.setup()
    return processor
```

### 3. 创建生成器

```python
# engines/your_engine/sentence_generators/01_text_generator.py
from core.base_sentence_generator import BaseSentenceGenerator

class TextGenerator(BaseSentenceGenerator):
    """文本生成器"""

    param_config = {
        "Speaker": {"translate_type": "Speaker"},
        "Text": {}
    }

    @property
    def category(self) -> str:
        return "text"

    def process(self, data):
        """处理数据"""
        if not self.can_process(data):
            return None

        speaker = data.get("Speaker", "")
        text = data.get("Text", "")

        if not text:
            return None

        if speaker:
            return [f"{speaker}: {text}"]
        else:
            return [text]
```

### 4. 创建参数映射

创建 `param_config/param_data_your_engine.xlsx`，包含参数映射。

### 5. 测试引擎

```python
# tests/engines/your_engine/test_text_generator.py
import pytest
from engines.your_engine.sentence_generators.text_generator import TextGenerator

class TestTextGenerator:
    def test_basic_text(self):
        # 测试代码
        pass
```

---

## 添加新生成器

### 1. 创建生成器文件

文件名使用数字前缀表示优先级：

```
engines/renpy/sentence_generators/
├── 01_text_generator.py      # 优先级 1
├── 02_audio_generator.py     # 优先级 2
└── 10_background_generator.py # 优先级 10
```

### 2. 实现生成器

```python
from core.base_sentence_generator import BaseSentenceGenerator

class YourGenerator(BaseSentenceGenerator):
    """你的生成器"""

    # 参数配置
    param_config = {
        "YourParam": {
            "translate_type": "YourParam",
            "format": "your_command {value}"
        }
    }

    @property
    def category(self) -> str:
        """生成器类别"""
        return "your_category"

    def process(self, data):
        """
        处理数据

        Args:
            data: 行数据字典

        Returns:
            List[str] or None: 生成的命令列表
        """
        if not self.can_process(data):
            return None

        # 翻译参数
        translated = self.do_translate(data)

        # 生成命令
        value = translated.get("YourParam", "")
        if not value:
            return None

        return [f"your_command {value}"]
```

### 3. 编写测试

```python
# tests/engines/renpy/test_your_generator.py
import pytest
from unittest.mock import Mock
from engines.renpy.sentence_generators.your_generator import YourGenerator

class TestYourGenerator:
    @pytest.fixture
    def generator(self):
        translator = Mock()
        config = Mock()
        return YourGenerator(translator, config)

    def test_process(self, generator):
        data = {"YourParam": "value"}
        result = generator.process(data)
        assert result == ["your_command value"]
```

---

## 调试技巧

### 1. 使用日志

```python
from core.logger import get_logger

logger = get_logger()

logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")
```

### 2. 使用 pdb 调试器

```python
import pdb

def your_function():
    # 设置断点
    pdb.set_trace()
    # 代码继续执行
```

### 3. 使用 pytest 调试

```bash
# 在测试失败时进入调试器
pytest tests/ --pdb

# 在测试开始时进入调试器
pytest tests/ --trace
```

### 4. 查看日志

```bash
# 实时查看日志
tail -f logs/scenario_tool.log

# Windows
Get-Content logs/scenario_tool.log -Wait
```

---

## 性能优化

### 1. 使用性能分析

```python
import cProfile
import pstats

def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()

    # 你的代码

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)
```

### 2. 优化建议

- 避免在循环中进行重复计算
- 使用生成器而不是列表（当数据量大时）
- 缓存频繁访问的数据
- 使用批处理减少 I/O 操作

---

## 发布流程

### 1. 更新版本号

更新相关文件中的版本号。

### 2. 更新 CHANGELOG

记录本次发布的变更。

### 3. 运行完整测试

```bash
# 运行所有测试
pytest tests/ -v

# 检查覆盖率
pytest --cov=. --cov-report=html

# 运行集成测试
py _test_all.py
```

### 4. 创建发布标签

```bash
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

---

## 常见问题

### 如何添加新的配置选项？

1. 在 `core/config_manager.py` 中添加配置类
2. 更新 `config.yaml` 示例
3. 更新文档

### 如何添加新的常量？

在 `core/constants.py` 中添加：

```python
class YourEnum(str, Enum):
    """你的枚举"""
    VALUE1 = "value1"
    VALUE2 = "value2"
```

### 如何处理异常？

使用项目定义的异常类：

```python
from core.exceptions import ScenarioToolError

raise ScenarioToolError("错误信息")
```

---

## 贡献指南

### 提交 Issue

- 使用清晰的标题
- 提供详细的描述
- 包含复现步骤
- 附上相关日志

### 提交 Pull Request

- 确保所有测试通过
- 更新相关文档
- 遵循代码规范
- 编写清晰的提交信息

### 提交信息规范

使用约定式提交：

```
feat: 添加新功能
fix: 修复 bug
docs: 更新文档
style: 代码格式调整
refactor: 重构代码
test: 添加测试
chore: 构建/工具变更
```

---

## 下一步

- [架构设计](architecture.md) - 了解项目架构
- [测试指南](testing.md) - 编写测试
- [常见问题](faq.md) - 开发相关问题

---

## 相关资源

- [Python PEP 8](https://pep8.org/) - Python 代码风格指南
- [pytest 文档](https://docs.pytest.org/) - pytest 测试框架
