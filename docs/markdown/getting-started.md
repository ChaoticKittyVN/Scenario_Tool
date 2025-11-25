# 快速开始

本指南将帮助你快速上手 Scenario Tool。

## 安装依赖

### 生产环境

```bash
pip install -r requirements.txt
```

这将安装以下依赖：
- `pandas` - 数据处理
- `openpyxl` - Excel 文件读写
- `pyyaml` - 配置文件解析
- `PySide6` - GUI 界面（可选）

### 开发环境

如果你需要开发或运行测试：

```bash
pip install -r requirements-dev.txt
```

---

## GUI 模式

GUI 模式提供了友好的图形界面，适合不熟悉命令行的用户。

### 启动 GUI

```bash
py run_gui.py
```

### GUI 功能

GUI 提供四个功能标签页：

1. **脚本生成**
   - 选择 Excel 文件
   - 选择输出目录
   - 一键生成引擎脚本

2. **参数映射**
   - 更新参数映射配置
   - 自动同步到演出表格

3. **资源管理**
   - 验证资源文件完整性
   - 同步缺失的资源文件

4. **默认配置**
   - 修改全局配置
   - 切换引擎类型

---

## 命令行模式

命令行模式适合自动化和批处理场景。

### 1. 配置引擎

编辑 `config.yaml`，选择目标引擎：

```yaml
engine:
  engine_type: "renpy"  # 或 "naninovel"
```

### 2. 准备数据

将 Excel 文件放入 `input/` 目录。

**Excel 格式要求**：
- 必须包含 `Note` 列，用 "END" 标记数据结束
- 可选 `Ignore` 列，标记需要忽略的行
- 其他列根据引擎类型而定（详见[配置说明](configuration.md)）

### 3. 生成脚本

```bash
py generate_scenario.py
```

生成的脚本保存在 `output/` 目录：
- Ren'Py: `.rpy` 文件
- Naninovel: `.nani` 文件

---

## 第一个示例

### 创建 Excel 文件

在 `input/` 目录创建 `test.xlsx`，包含以下内容：

| Note | Speaker | Text | Background |
|------|---------|------|------------|
| 场景1 | 旁白 | 这是一个测试 | bg_room |
| 场景2 | 角色A | 你好！ | bg_room |
| END | | | |

### 生成脚本

```bash
py generate_scenario.py
```

### 查看结果

在 `output/` 目录查看生成的脚本文件。

---

## 下一步

- [配置说明](configuration.md) - 了解详细的配置选项
- [参数映射](param-mapping.md) - 自定义参数映射
- [Excel 格式](configuration.md#excel-格式要求) - 详细的 Excel 格式说明

---

## 常见问题

### 找不到 Excel 文件？

确保：
1. Excel 文件在 `input/` 目录
2. 文件扩展名是 `.xlsx` 或 `.xls`
3. 文件名不以 `~` 开头（临时文件）

### 生成的脚本为空？

检查：
1. Excel 中是否有 "END" 标记
2. `Ignore` 列是否标记了所有行
3. 查看 `logs/scenario_tool.log` 了解详细错误

### 更多问题？

查看 [常见问题](faq.md) 或提交 Issue。
