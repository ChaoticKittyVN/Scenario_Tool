# 参数映射管理

参数映射系统允许你将 Excel 中的中文参数自动翻译为引擎脚本中的实际参数。

## 概述

参数映射的工作流程：

```
Excel 中文参数 → 参数映射文件 → 引擎脚本参数
   "音乐1"    →  param_mappings.py  →   "music1"
```

---

## 参数文件位置

- **Ren'Py**: `param_config/param_data_renpy.xlsx`
- **Naninovel**: `param_config/param_data_naninovel.xlsx`
- **差分参数**: `param_config/varient_data.xlsx`（可选）

---

## 参数文件格式

### 基础参数文件

每个工作表代表一个参数类型，包含两列：

| 列名 | 说明 |
|------|------|
| `ExcelParam` | Excel 中使用的中文参数 |
| `ScenarioParam` | 引擎脚本中的实际参数 |

### 示例：Speaker 工作表

| ExcelParam | ScenarioParam |
|------------|---------------|
| 爱丽丝 | alice |
| 鲍勃 | bob |
| 旁白 | narrator |

### 示例：Music 工作表

| ExcelParam | ScenarioParam |
|------------|---------------|
| 主题曲 | bgm_main |
| 战斗音乐 | bgm_battle |
| 悲伤音乐 | bgm_sad |

---

## 差分参数文件

差分参数用于角色表情、姿势等变化。

### 格式

每个工作表代表一个角色，包含该角色的所有差分：

**工作表名**: 角色名（如 "爱丽丝"）

| ExcelParam | ScenarioParam |
|------------|---------------|
| 开心 | happy |
| 难过 | sad |
| 生气 | angry |
| 惊讶 | surprised |

---

## 更新参数映射

### 1. 编辑参数文件

使用 Excel 编辑对应引擎的参数文件：

```bash
# 编辑 Ren'Py 参数
param_config/param_data_renpy.xlsx

# 编辑 Naninovel 参数
param_config/param_data_naninovel.xlsx

# 编辑差分参数（可选）
param_config/varient_data.xlsx
```

### 2. 运行更新脚本

```bash
py update_param.py
```

### 3. 自动生成映射文件

脚本会自动生成以下文件：

- `param_config/param_mappings.py` - 基础参数映射
- `param_config/varient_mappings.py` - 差分参数映射（如果存在）

### 4. 重新生成脚本

```bash
py generate_scenario.py
```

---

## 完整工作流程

```mermaid
graph LR
    A[编辑参数文件] --> B[运行 update_param.py]
    B --> C[生成 param_mappings.py]
    C --> D[更新演出表格参数表]
    D --> E[运行 generate_scenario.py]
    E --> F[生成引擎脚本]
```

1. **编辑参数文件**（Excel）
2. **运行** `py update_param.py`
3. **自动生成** `param_config/param_mappings.py`
4. **自动更新**演出表格中的"参数表"工作表
5. **重新运行** `py generate_scenario.py` 生成脚本

---

## 参数表自动更新

`update_param.py` 会自动更新 `input/` 目录中所有 Excel 文件的"参数表"工作表。

### 参数表的作用

- 提供参数验证（Excel 数据验证下拉列表）
- 确保参数拼写正确
- 方便查看所有可用参数

### 参数表格式

参数表包含多列，每列对应一个参数类型：

| Speaker | Music | Background | ... |
|---------|-------|------------|-----|
| 爱丽丝 | 主题曲 | 房间 | ... |
| 鲍勃 | 战斗音乐 | 街道 | ... |
| 旁白 | 悲伤音乐 | 森林 | ... |

### 命名区域

参数表会自动创建命名区域（如 `SpeakerList`），用于 Excel 数据验证。

---

## 高级用法

### 1. 多对一映射

多个中文参数可以映射到同一个引擎参数：

| ExcelParam | ScenarioParam |
|------------|---------------|
| 主角 | protagonist |
| 男主 | protagonist |
| 女主 | protagonist |

### 2. 特殊字符处理

参数名可以包含特殊字符：

| ExcelParam | ScenarioParam |
|------------|---------------|
| 音乐-1 | music_1 |
| 音乐_2 | music_2 |
| 音乐(3) | music_3 |

### 3. 空参数处理

空参数会被保留：

| ExcelParam | ScenarioParam |
|------------|---------------|
| （空） | （空） |

---

## 参数映射示例

### Ren'Py 完整示例

**param_data_renpy.xlsx**:

**Speaker 工作表**:
| ExcelParam | ScenarioParam |
|------------|---------------|
| 爱丽丝 | alice |
| 鲍勃 | bob |

**Music 工作表**:
| ExcelParam | ScenarioParam |
|------------|---------------|
| 主题曲 | "audio/bgm_main.mp3" |
| 战斗音乐 | "audio/bgm_battle.mp3" |

**Background 工作表**:
| ExcelParam | ScenarioParam |
|------------|---------------|
| 房间 | bg_room |
| 街道 | bg_street |

### 差分参数示例

**varient_data.xlsx**:

**爱丽丝 工作表**:
| ExcelParam | ScenarioParam |
|------------|---------------|
| 开心 | happy |
| 难过 | sad |
| 生气 | angry |

**鲍勃 工作表**:
| ExcelParam | ScenarioParam |
|------------|---------------|
| 正常 | normal |
| 惊讶 | surprised |

---

## 故障排除

### 参数映射未生效？

1. 确认运行了 `py update_param.py`
2. 检查 `param_config/param_mappings.py` 是否已更新
3. 重新运行 `py generate_scenario.py`

### 参数表未更新？

1. 确认 Excel 文件在 `input/` 目录
2. 确认 Excel 文件包含"参数表"工作表
3. 检查 `logs/scenario_tool.log` 查看错误信息

### 参数翻译错误？

1. 检查参数文件中的拼写
2. 确认 `ExcelParam` 和 `ScenarioParam` 列名正确
3. 确认工作表名称正确

---

## 最佳实践

### 1. 使用有意义的参数名

```
✅ 推荐：
ExcelParam: "主题曲"
ScenarioParam: "bgm_main"

❌ 不推荐：
ExcelParam: "音乐1"
ScenarioParam: "m1"
```

### 2. 保持参数一致性

所有 Excel 文件应使用相同的参数名称。

### 3. 定期备份参数文件

参数文件是项目的重要配置，建议纳入版本控制。

### 4. 文档化特殊参数

对于复杂的参数映射，添加注释说明。

---

## 下一步

- [配置说明](configuration.md) - 了解配置选项
- [快速开始](getting-started.md) - 开始使用工具
- [常见问题](faq.md) - 参数映射相关问题

---

## 相关文件

- `param_config/param_data_renpy.xlsx` - Ren'Py 参数文件
- `param_config/param_data_naninovel.xlsx` - Naninovel 参数文件
- `param_config/varient_data.xlsx` - 差分参数文件
- `param_config/param_mappings.py` - 生成的参数映射（自动生成）
- `param_config/varient_mappings.py` - 生成的差分映射（自动生成）
- `update_param.py` - 参数更新脚本
