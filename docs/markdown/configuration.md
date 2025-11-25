# 配置说明

本文档详细说明 Scenario Tool 的配置选项。

## 配置文件

配置文件为 `config.yaml`，位于项目根目录。

---

## 引擎配置

### 切换引擎

只需修改 `engine_type` 即可切换引擎：

```yaml
# Ren'Py 引擎
engine:
  engine_type: "renpy"

# Naninovel 引擎
engine:
  engine_type: "naninovel"
```

### Ren'Py 引擎配置

```yaml
engine:
  engine_type: "renpy"
  indent_size: 4                      # 缩进大小（默认：4）
  default_transition: "dissolve"      # 默认转场效果
  file_extension: ".rpy"              # 输出文件扩展名
```

### Naninovel 引擎配置

```yaml
engine:
  engine_type: "naninovel"
  indent_size: 4                      # 缩进大小（默认：4）
  file_extension: ".nani"             # 输出文件扩展名
```

---

## 路径配置

配置输入输出目录：

```yaml
paths:
  input_dir: "./input"                # Excel 输入目录
  output_dir: "./output"              # 脚本输出目录
  param_config_dir: "./param_config"  # 参数映射目录
```

**说明**：
- `input_dir`: 存放 Excel 演出表格的目录
- `output_dir`: 生成的引擎脚本保存目录
- `param_config_dir`: 参数映射配置文件目录

---

## 处理配置

控制脚本生成行为：

```yaml
processing:
  ignore_mode: true                   # 启用忽略模式
  ignore_words: ["忽略", ""]          # 忽略标记词
  enable_progress_bar: true           # 显示进度条
```

**说明**：
- `ignore_mode`: 启用后，会跳过 `Ignore` 列标记的行
- `ignore_words`: 当 `Ignore` 列包含这些词时，该行会被忽略
- `enable_progress_bar`: 是否显示处理进度条

---

## Excel 格式要求

### 必需列

| 列名 | 说明 | 必需 |
|------|------|------|
| `Note` | 注释列，必须包含 "END" 标记表示数据结束 | ✅ |
| `Ignore` | 忽略标记列 | ❌ |

### Ren'Py 支持的列

| 列名 | 说明 | 示例 |
|------|------|------|
| `Speaker` | 说话人 | "角色A" |
| `Text` | 对话文本 | "你好！" |
| `Character` | 角色名称 | "alice" |
| `Sprite` | 角色立绘 | "happy" |
| `Background` | 背景图片 | "bg_room" |
| `Music` | 背景音乐 | "bgm_main" |
| `Sound` | 音效 | "sfx_door" |
| `Voice` | 语音 | "voice_001" |
| `Transition` | 转场效果 | "dissolve" |
| `Window` | 对话框显示/隐藏 | "显示" / "隐藏" |
| `Pause` | 暂停时间（秒） | "2.0" |

### Naninovel 支持的列

| 列名 | 说明 | 示例 |
|------|------|------|
| `Speaker` | 说话人 | "角色A" |
| `Text` | 对话文本 | "你好！" |
| `Char` | 角色 | "Alice" |
| `Background` | 背景 | "Room" |
| `Music` | 背景音乐 | "MainTheme" |
| `Sound` | 音效 | "DoorOpen" |
| `Camera` | 镜头控制 | "zoom:1.5" |
| `Effect` | 特效 | "Rain" |
| `Movie` | 视频 | "opening" |
| `Wait` | 等待时间（秒） | "2.0" |

### 特殊工作表

- **`参数表`**: 此工作表会被自动跳过，不生成脚本
  - 用于存储参数验证数据
  - 由 `update_param.py` 自动维护

---

## Excel 示例

### 基础对话示例

| Note | Speaker | Text | Background |
|------|---------|------|------------|
| 场景1 | 旁白 | 故事开始了 | bg_room |
| 场景2 | 角色A | 你好！ | bg_room |
| 场景3 | 角色B | 很高兴见到你 | bg_room |
| END | | | |

### 完整示例（Ren'Py）

| Note | Speaker | Text | Character | Sprite | Background | Music | Transition |
|------|---------|------|-----------|--------|------------|-------|------------|
| 开场 | | | | | bg_title | bgm_title | fade |
| 场景1 | 旁白 | 这是一个美好的早晨 | | | bg_room | bgm_main | dissolve |
| 场景2 | 爱丽丝 | 早上好！ | alice | happy | | | |
| 场景3 | 鲍勃 | 早上好，爱丽丝 | bob | normal | | | |
| END | | | | | | | |

---

## 配置最佳实践

### 1. 使用相对路径

```yaml
paths:
  input_dir: "./input"      # ✅ 推荐
  output_dir: "./output"    # ✅ 推荐
```

避免使用绝对路径，以便项目可移植。

### 2. 合理设置忽略词

```yaml
processing:
  ignore_words: ["忽略", "跳过", ""]  # 支持多个标记词
```

### 3. 引擎特定配置

不同引擎可能需要不同的配置，建议为每个引擎创建独立的配置文件：

```bash
config_renpy.yaml
config_naninovel.yaml
```

使用时指定配置文件（如果工具支持）。

---

## 下一步

- [参数映射](param-mapping.md) - 自定义参数翻译
- [快速开始](getting-started.md) - 开始使用工具
- [常见问题](faq.md) - 配置相关问题

---

## 相关文件

- `config.yaml` - 主配置文件
- `param_config/param_data_renpy.xlsx` - Ren'Py 参数映射
- `param_config/param_data_naninovel.xlsx` - Naninovel 参数映射
