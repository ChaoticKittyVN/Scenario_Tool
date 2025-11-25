# 测试指南

本文档介绍如何运行和编写测试。

## 测试概述

Scenario Tool 使用 pytest 作为测试框架，当前测试覆盖率为 **92%**（250 个测试）。

---

## 安装测试依赖

```bash
pip install -r requirements-dev.txt
```

这将安装：
- `pytest` - 测试框架
- `pytest-cov` - 测试覆盖率
- `pytest-mock` - Mock 工具
- `pytest-xdist` - 并行测试
- `pytest-timeout` - 测试超时
- `black` - 代码格式化（可选）
- `flake8` - 代码检查（可选）
- `mypy` - 类型检查（可选）

---

## 运行测试

### 运行所有测试

```bash
pytest tests/ -v
```

### 运行特定模块的测试

```bash
# 运行 core 模块测试
pytest tests/core/ -v

# 运行 engines 模块测试（待实现）
pytest tests/engines/ -v
```

### 运行特定测试文件

```bash
pytest tests/core/test_param_translator.py -v
```

### 运行特定测试函数

```bash
pytest tests/core/test_param_translator.py::TestParamTranslator::test_translate -v
```

---

## 测试覆盖率

### 生成覆盖率报告

```bash
# 终端输出
pytest --cov=. --cov-report=term-missing

# HTML 报告
pytest --cov=. --cov-report=html

# 两者都生成
pytest --cov=. --cov-report=term-missing --cov-report=html
```

### 查看 HTML 报告

```bash
# Windows
start htmlcov/index.html

# Linux/Mac
open htmlcov/index.html
```

### 当前覆盖率状况

✅ **总体覆盖率：92%**（250 个测试）

**核心模块覆盖率**：
- ✅ `core/config_manager.py` - 100% 覆盖（31 个测试）
- ✅ `core/constants.py` - 100% 覆盖（42 个测试）
- ✅ `core/engine_processor.py` - 100% 覆盖（19 个测试）
- ✅ `core/engine_registry.py` - 100% 覆盖（19 个测试）
- ✅ `core/exceptions.py` - 100% 覆盖
- ✅ `core/base_sentence_generator.py` - 97% 覆盖（44 个测试）
- ✅ `core/param_translator.py` - 85% 覆盖（19 个测试）
- ✅ `core/sentence_generator_manager.py` - 82% 覆盖（23 个测试）
- ✅ `update_param.py` - 89% 覆盖（34 个测试）

---

## 测试目录结构

```
tests/
├── __init__.py
├── conftest.py                              # 全局 fixtures
├── core/                                    # 核心模块测试
│   ├── __init__.py
│   ├── test_base_sentence_generator.py      # 基础生成器测试
│   ├── test_config_manager.py               # 配置管理测试
│   ├── test_constants.py                    # 常量定义测试
│   ├── test_engine_processor.py             # 引擎处理器测试
│   ├── test_engine_registry.py              # 引擎注册表测试
│   ├── test_param_translator.py             # 参数翻译器测试
│   └── test_sentence_generator_manager.py   # 生成器管理器测试
├── engines/                                 # 引擎模块测试（待扩展）
│   └── __init__.py
├── gui/                                     # GUI 模块测试（待扩展）
│   └── __init__.py
└── test_param_updater.py                    # 参数更新器测试
```

---

## 测试特性

### 1. 参数化测试

使用 `@pytest.mark.parametrize` 减少代码重复：

```python
@pytest.mark.parametrize("param_type,param_value,expected", [
    ("Music", "音乐1", "music1"),
    ("Music", "音乐2", "music2"),
    ("Speaker", "角色A", "character_a"),
])
def test_translate(self, translator, param_type, param_value, expected):
    """测试参数翻译"""
    assert translator.translate(param_type, param_value) == expected
```

### 2. Fixture 支持

提供可复用的测试组件：

```python
@pytest.fixture
def mock_translator(self):
    """创建模拟的翻译器"""
    translator = Mock(spec=ParamTranslator)
    translator.translate.side_effect = lambda type_, value: f"translated_{value}"
    return translator
```

### 3. Mock 对象隔离

使用 Mock 确保单元测试的独立性：

```python
from unittest.mock import Mock, patch

def test_with_mock(self):
    mock_obj = Mock()
    mock_obj.method.return_value = "mocked"
    assert mock_obj.method() == "mocked"
```

### 4. 临时文件系统

使用 `tmp_path` fixture 避免测试污染：

```python
def test_with_temp_file(self, tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    assert test_file.read_text() == "content"
```

---

## 集成测试

运行集成测试：

```bash
py _test_all.py
```

集成测试内容：
- 模块导入
- 彩色日志系统
- 配置管理（引擎切换）
- 引擎注册表
- 参数翻译器
- 异常系统
- 常量管理
- 参数映射更新

---

## 编写测试

### 测试文件命名

- 测试文件以 `test_` 开头
- 测试类以 `Test` 开头
- 测试函数以 `test_` 开头

```python
# tests/core/test_example.py
class TestExample:
    def test_something(self):
        assert True
```

### 测试组织

按功能组织测试类：

```python
class TestBasicFunctionality:
    """测试基础功能"""

    def test_feature_a(self):
        pass

    def test_feature_b(self):
        pass

class TestAdvancedFunctionality:
    """测试高级功能"""

    def test_feature_c(self):
        pass
```

### 使用 Fixtures

```python
@pytest.fixture
def sample_data(self):
    """提供测试数据"""
    return {"key": "value"}

def test_with_fixture(self, sample_data):
    assert sample_data["key"] == "value"
```

### 参数化测试

```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_double(self, input, expected):
    assert input * 2 == expected
```

---

## 测试最佳实践

### 1. 测试命名要清晰

```python
# ✅ 好的命名
def test_translate_returns_correct_value_for_valid_input(self):
    pass

# ❌ 不好的命名
def test_1(self):
    pass
```

### 2. 一个测试只测一件事

```python
# ✅ 好的做法
def test_translate_with_valid_input(self):
    result = translator.translate("Music", "音乐1")
    assert result == "music1"

def test_translate_with_invalid_input(self):
    result = translator.translate("Music", "不存在")
    assert result == "不存在"
```

### 3. 使用有意义的断言消息

```python
# ✅ 好的做法
assert result == expected, f"Expected {expected}, got {result}"
```

### 4. 测试边界条件

```python
def test_with_empty_string(self):
    assert translator.translate("Music", "") == ""

def test_with_none(self):
    assert translator.translate("Music", None) == None

def test_with_special_characters(self):
    assert translator.translate("Music", "音乐-1") == "music_1"
```

### 5. 保持测试独立

每个测试应该独立运行，不依赖其他测试的状态。

---

## 待完成测试

- [ ] `tests/test_resource_validator.py` - 资源验证测试
- [ ] `tests/test_resource_syncer.py` - 资源同步测试
- [ ] `tests/engines/renpy/` - Ren'Py 引擎生成器测试
- [ ] `tests/engines/naninovel/` - Naninovel 引擎生成器测试
- [ ] `tests/gui/` - GUI 模块测试

---

## 故障排除

### 测试失败？

1. 查看详细错误信息：`pytest tests/ -v`
2. 运行单个失败的测试：`pytest tests/core/test_xxx.py::test_yyy -v`
3. 使用 `--pdb` 进入调试器：`pytest tests/ --pdb`

### 导入错误？

确保项目根目录在 Python 路径中：
```bash
# Windows
set PYTHONPATH=%PYTHONPATH%;%CD%

# Linux/Mac
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### 覆盖率不准确？

清除缓存后重新运行：
```bash
pytest --cache-clear --cov=. --cov-report=html
```

---

## 下一步

- [开发指南](development.md) - 贡献代码
- [架构设计](architecture.md) - 了解项目架构
- [常见问题](faq.md) - 测试相关问题

---

## 相关文件

- `tests/` - 测试目录
- `tests/conftest.py` - 全局 fixtures
- `_test_all.py` - 集成测试脚本
- `requirements-dev.txt` - 开发依赖
