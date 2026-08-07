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
- **Utage**: `param_config/param_data_utage.xlsx`
- **差分参数**: `param_config/variant_data.xlsx`（可选）

单项目和多项目的参数文件选择规则见[配置说明](configuration.md#项目与篇章参数)。

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

每个工作表代表一个角色或差分集合。普通映射只要求 `ExcelParam` 和 `ScenarioParam`；Agent 文档模式还可以读取任意自定义描述列：

**工作表名**: 角色名（如 "爱丽丝"）

| ExcelParam | ScenarioParam | 情绪 | 序号 | 适用情绪 | 眼 | 嘴 |
|------------|---------------|------|------|----------|----|----|
| 开心1 | happy1 | 开心 | 1 | 开心、日常 | 弯眼 | 微笑 |
| 开心2 | happy2 | 开心 | 2 | 开心、得意 | 睁眼 | 张嘴 |

自定义列不会改变普通 `variant_mappings.py` 的行为，只会在 Agent 文档中作为结构化属性保留。

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
param_config/variant_data.xlsx
```

### 2. 运行更新脚本

```bash
py update_param.py
```

默认直接执行会保持原有流程：生成基础与差分映射，并把 `param_data`、`variant_data` 同步到 `input/` 中演出表格的参数表。

可以先预览：

```bash
py update_param.py --dry-run
```

也可以只执行一个阶段：

```bash
# 只生成基础和差分映射模块
py update_param.py --mappings-only

# 只同步演出工作簿中的参数表
py update_param.py --parameter-sheet-only

# 只生成普通差分映射
py update_param.py --variant-mappings-only

# 只生成 Agent 差分 JSON
py update_param.py --agent-variant-doc-only
```

### 3. 自动生成映射文件

脚本会自动生成以下文件：

- `param_config/param_mappings.py` - 基础参数映射
- `param_config/variant_mappings.py` - 差分参数映射（如果存在）
- `param_config/variant_agent_data.json` - Agent 差分文档（显式执行或配置启用时）

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

`update_param.py` 会自动更新 `input/` 目录中所有 Excel 文件的“参数表”工作表。缺少参数表时会创建；内容完全一致时跳过保存。

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

**variant_data.xlsx**:

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
2. 使用 `py update_param.py --parameter-sheet-only --dry-run` 检查文件选择和参数来源
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
- `param_config/param_data_utage.xlsx` - Utage 参数文件
- `param_config/variant_data.xlsx` - 差分参数文件
- `param_config/param_mappings.py` - 生成的参数映射（自动生成）
- `param_config/variant_mappings.py` - 生成的差分映射（自动生成）
- `param_config/variant_agent_data.json` - Agent 差分文档（按需生成）
- `update_param.py` - 参数更新脚本
