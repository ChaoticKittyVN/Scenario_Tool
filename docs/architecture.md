# 架构设计

本文档介绍 Scenario Tool 的架构设计和核心概念。

## 设计理念

Scenario Tool 采用**插件化架构**，核心设计理念包括：

1. **引擎无关**: 核心框架不依赖特定引擎
2. **可扩展性**: 易于添加新引擎和生成器
3. **模块化**: 功能模块独立，职责清晰
4. **可测试性**: 高测试覆盖率，易于单元测试

---

## 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                     用户界面层                           │
│  ┌──────────────┐              ┌──────────────┐        │
│  │  GUI 界面    │              │  命令行工具   │        │
│  └──────────────┘              └──────────────┘        │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────┐
│                     应用层                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ 脚本生成工具  │  │ 参数映射工具  │  │ 资源管理工具  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────┐
│                     核心框架层                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ 引擎处理器    │  │ 参数翻译器    │  │ 配置管理器    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ 引擎注册表    │  │ 生成器管理器  │  │ 日志系统      │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────┐
│                     引擎层                               │
│  ┌──────────────┐              ┌──────────────┐        │
│  │ Ren'Py 引擎  │              │Naninovel引擎 │        │
│  │ ┌──────────┐ │              │ ┌──────────┐ │        │
│  │ │生成器集合│ │              │ │生成器集合│ │        │
│  │ └──────────┘ │              │ └──────────┘ │        │
│  └──────────────┘              └──────────────┘        │
└─────────────────────────────────────────────────────────┘
```

---

## 核心组件

### 1. 引擎注册表 (EngineRegistry)

**职责**: 管理所有可用引擎的注册和查询

**设计模式**: 单例模式

**关键方法**:
```python
class EngineRegistry:
    def register(self, name: str, metadata: EngineMetadata)
    def get(self, name: str) -> EngineMetadata
    def is_registered(self, name: str) -> bool
    def list_engines(self) -> List[str]
```

**使用示例**:
```python
@register_engine(
    name="renpy",
    display_name="Ren'Py",
    file_extension=".rpy"
)
def create_renpy_processor(config, translator):
    return processor
```

### 2. 配置管理器 (ConfigManager)

**职责**: 管理应用配置和引擎配置

**设计模式**: 数据类 + 工厂模式

**配置层次**:
```
AppConfig
├── PathConfig        # 路径配置
├── ProcessingConfig  # 处理配置
└── EngineConfig      # 引擎配置
    ├── RenpyConfig
    └── NaninovelConfig
```

**关键方法**:
```python
class AppConfig:
    @classmethod
    def from_file(cls, path: Path) -> AppConfig

    @classmethod
    def create_default(cls, engine_type: str) -> AppConfig

    def to_file(self, path: Path)
```

### 3. 参数翻译器 (ParamTranslator)

**职责**: 将 Excel 中的中文参数翻译为引擎参数

**设计模式**: 策略模式

**翻译流程**:
```
Excel 参数 → 参数映射表 → 引擎参数
  "音乐1"  →  PARAM_MAPPINGS  →  "music1"
```

**关键方法**:
```python
class ParamTranslator:
    def translate(self, param_type: str, param_value: str) -> str
    def translate_varient(self, param_value: str, role: str = None) -> str
    def translate_batch(self, param_type: str, params: List[str]) -> List[str]
```

### 4. 生成器管理器 (SentenceGeneratorManager)

**职责**: 动态发现和管理句子生成器

**设计模式**: 工厂模式 + 策略模式

**工作流程**:
```
1. 扫描引擎目录
2. 发现生成器类
3. 收集参数配置
4. 创建生成器实例
5. 按优先级排序
```

**关键方法**:
```python
class SentenceGeneratorManager:
    def load(self)
    def create_generator_instances(self, translator, config) -> List[BaseSentenceGenerator]
    def get_all_param_names(self) -> Set[str]
```

### 5. 引擎处理器 (EngineProcessor)

**职责**: 协调生成器处理 Excel 数据

**设计模式**: 管道模式

**处理流程**:
```
Excel 行数据 → 生成器1 → 生成器2 → ... → 生成器N → 脚本命令
```

**关键方法**:
```python
class EngineProcessor:
    def setup(self)
    def process_row(self, row_data: pd.Series) -> List[str]
    def get_pipeline_info(self) -> Dict
```

### 6. 基础生成器 (BaseSentenceGenerator)

**职责**: 提供生成器的基础功能

**设计模式**: 模板方法模式

**生成器结构**:
```python
class BaseSentenceGenerator(ABC):
    # 参数配置
    param_config: Dict[str, Dict] = {}

    # 抽象方法
    @property
    @abstractmethod
    def category(self) -> str:
        pass

    @abstractmethod
    def process(self, data) -> Optional[List[str]]:
        pass

    # 工具方法
    def can_process(self, data) -> bool
    def do_translate(self, data) -> Dict
    def get_value(self, param_name, data, use_default=False) -> str
    def get_sentence(self, param_name, data, use_default=False) -> str
```

---

## 数据流

### 脚本生成流程

```
1. 读取 Excel 文件
   ↓
2. 遍历每一行
   ↓
3. 引擎处理器处理行数据
   ├─→ 生成器1.can_process(data) → 是 → process(data) → 命令1
   ├─→ 生成器2.can_process(data) → 是 → process(data) → 命令2
   └─→ 生成器N.can_process(data) → 否 → 跳过
   ↓
4. 收集所有命令
   ↓
5. 写入脚本文件
```

### 参数翻译流程

```
1. 读取参数文件 (Excel)
   ↓
2. 解析工作表和映射
   ↓
3. 生成 param_mappings.py
   ↓
4. ParamTranslator 加载映射
   ↓
5. 生成器调用 translate()
   ↓
6. 返回翻译后的参数
```

---

## 扩展机制

### 添加新引擎

1. **创建引擎目录**:
   ```
   engines/your_engine/
   ├── __init__.py
   └── sentence_generators/
       ├── 01_text_generator.py
       └── 02_audio_generator.py
   ```

2. **注册引擎**:
   ```python
   @register_engine(
       name="your_engine",
       display_name="Your Engine",
       file_extension=".ext"
   )
   def create_processor(config, translator):
       return EngineProcessor("your_engine", translator, config)
   ```

3. **实现生成器**:
   ```python
   class TextGenerator(BaseSentenceGenerator):
       param_config = {"Text": {}}

       @property
       def category(self) -> str:
           return "text"

       def process(self, data):
           return [f"text: {data['Text']}"]
   ```

### 添加新生成器

1. **创建生成器文件**: `XX_your_generator.py`（XX 为优先级）

2. **继承基类**: 继承 `BaseSentenceGenerator`

3. **实现必需方法**:
   - `category` 属性
   - `process()` 方法

4. **配置参数**: 设置 `param_config`

---

## 设计模式

### 1. 单例模式

**应用**: `EngineRegistry`

**目的**: 确保全局只有一个引擎注册表实例

### 2. 工厂模式

**应用**: 引擎创建、生成器创建

**目的**: 解耦对象创建和使用

### 3. 策略模式

**应用**: 参数翻译、生成器处理

**目的**: 支持多种算法/策略的动态切换

### 4. 模板方法模式

**应用**: `BaseSentenceGenerator`

**目的**: 定义算法骨架，子类实现具体步骤

### 5. 管道模式

**应用**: `EngineProcessor` 的数据处理流程

**目的**: 将数据处理分解为多个独立的步骤

### 6. 装饰器模式

**应用**: `@register_engine` 装饰器

**目的**: 动态添加功能（引擎注册）

---

## 关键设计决策

### 1. 为什么使用插件化架构？

**优点**:
- 易于添加新引擎
- 引擎之间相互独立
- 核心框架稳定

**缺点**:
- 增加了一定的复杂度
- 需要良好的文档支持

### 2. 为什么使用优先级系统？

生成器使用数字前缀表示优先级（如 `01_text_generator.py`）：

**优点**:
- 明确的执行顺序
- 易于调整优先级
- 直观可见

**缺点**:
- 需要手动管理文件名

### 3. 为什么分离参数映射？

参数映射独立于代码（Excel 文件）：

**优点**:
- 非程序员可以修改
- 易于维护和更新
- 支持多语言

**缺点**:
- 需要额外的更新步骤
- 可能出现映射不一致

### 4. 为什么使用 YAML 配置？

**优点**:
- 人类可读
- 支持注释
- 易于编辑

**缺点**:
- 需要额外的解析库
- 语法相对严格

---

## 性能考虑

### 1. 延迟加载

生成器只在需要时才被加载和实例化。

### 2. 缓存机制

参数翻译结果可以被缓存以提高性能。

### 3. 批处理

Excel 数据按批次处理，减少内存占用。

### 4. 并行处理

未来可以支持多进程并行处理多个 Excel 文件。

---

## 安全考虑

### 1. 输入验证

所有外部输入（Excel、配置文件）都需要验证。

### 2. 路径安全

使用 `Path` 对象处理文件路径，防止路径遍历攻击。

### 3. 异常处理

所有可能的异常都被捕获和记录。

---

## 未来扩展

### 1. 插件系统

支持第三方插件扩展功能。

### 2. Web 界面

提供基于 Web 的管理界面。

### 3. 云端处理

支持将处理任务提交到云端。

### 4. 实时预览

在编辑 Excel 时实时预览生成的脚本。

---

## 下一步

- [开发指南](development.md) - 开始开发
- [测试指南](testing.md) - 编写测试
- [常见问题](faq.md) - 架构相关问题

---

## 相关资源

- [设计模式](https://refactoring.guru/design-patterns) - 设计模式参考
- [Python 架构模式](https://www.cosmicpython.com/) - Python 架构最佳实践
