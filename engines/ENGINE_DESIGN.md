# 引擎设计说明

### Ren'Py 引擎

```
engines/renpy/
├── __init__.py              # 引擎注册
└── sentence_generators/     # 12个生成器
    ├── note_generator.py
    ├── audio_generator.py
    ├── character_generator.py
    └── ...
```

**特点**：
- ✅ 无需 `param_processor.py`
- ✅ 使用基类的 `get_sentence()` 方法处理参数
- ✅ 语法简单：空格分隔（如 `show alice happy at center with dissolve`）

### Naninovel 引擎

```
engines/naninovel/
├── __init__.py              # 引擎注册
├── param_processor.py       # ⭐ 参数处理器
└── sentence_generators/     # 7个生成器
    ├── note_generator.py
    ├── audio_generator.py
    ├── character_generator.py
    └── ...
```

**特点**：
- ✅ 需要 `param_processor.py`
- ✅ 处理键值对格式的参数
- ✅ 语法复杂：键值对（如 `@char Alice pose:smile visible:true time:2`）



### 代码示例对比

**Ren'Py 生成器**（无需 param_processor）：
```python
# 使用基类方法和 param_config 的 format 字段
at = self.get_sentence("SpriteAt", data)  # " at center"
transition = self.get_sentence("SpriteWith", data)  # " with dissolve"
line = f"{command}{image}{at}{transition}"
```

**Naninovel 生成器**（需要 param_processor）：
```python
# 需要统一的键值对格式化
pose = self.param_processor._process_pose_parameter(data.get("Pose"))  # " pose:smile"
visible = self.param_processor._process_visible_parameter(1)  # " visible:true"
result = f"{command}{image}{pose}{visible}"
```