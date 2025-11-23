# 资源管理

资源管理工具帮助你验证和同步项目中的资源文件（图片、音频、视频等）。

## 概述

资源管理包含两个主要功能：

1. **资源验证** - 检查 Excel 中引用的资源是否存在
2. **资源同步** - 从资源库复制缺失的资源到项目

---

## 资源验证

### 运行验证

```bash
py validate_resources.py
```

### 配置项目目录

编辑 `validate_resources.py` 中的 `project_dirs`（第262-266行）：

```python
project_dirs = {
    "图片": Path("project/images"),
    "音频": Path("project/audio"),
    "视频": Path("project/video"),
}
```

### 验证报告

报告保存在 `output/validation_reports/` 目录，包含：

- **统计信息**: 各类资源的总数和缺失数
- **缺失文件列表**: 详细列出所有缺失的资源
- **完成率**: 资源完整性百分比

### 报告示例

```
=== 资源验证报告 ===
生成时间: 2024-01-15 10:30:00

图片资源:
  总数: 150
  存在: 145
  缺失: 5
  完成率: 96.7%

音频资源:
  总数: 80
  存在: 75
  缺失: 5
  完成率: 93.8%

缺失文件:
  图片:
    - bg_room.png
    - char_alice_happy.png
  音频:
    - bgm_main.mp3
    - sfx_door.wav

总体完成率: 95.2%
```

---

## 资源同步

### 运行同步

```bash
py sync_resources.py
```

### 配置资源库目录

编辑 `sync_resources.py` 中的 `source_dirs`（第269-273行）：

```python
source_dirs = {
    "图片": Path("resource_library/images"),
    "音频": Path("resource_library/audio"),
    "视频": Path("resource_library/video"),
}
```

### 同步流程

1. **读取验证报告** - 获取缺失文件列表
2. **查找资源** - 在资源库中搜索缺失文件
3. **显示计划** - 列出将要复制的文件
4. **用户确认** - 询问是否执行同步
5. **选择模式** - 询问是否使用干跑模式
6. **执行复制** - 复制文件到项目目录

### 交互式同步示例

```
=== 资源同步计划 ===

找到的文件 (8):
  图片:
    bg_room.png → project/images/bg_room.png
    char_alice_happy.png → project/images/char_alice_happy.png
  音频:
    bgm_main.mp3 → project/audio/bgm_main.mp3

未找到的文件 (2):
  图片:
    missing_bg.png
  音频:
    missing_sfx.wav

是否执行同步? (y/N): y
是否为干跑模式（仅预览，不实际复制）? (y/N): n

开始同步...
已复制: bg_room.png → project/images/bg_room.png
已复制: char_alice_happy.png → project/images/char_alice_happy.png
已复制: bgm_main.mp3 → project/audio/bgm_main.mp3

同步结果:
  成功: 3
  失败: 0
  跳过: 0
  总计: 3
```

---

## 干跑模式

在同步过程中，工具会询问是否使用干跑模式：

```
是否为干跑模式（仅预览，不实际复制）? (y/N):
```

- 输入 `y`: 仅预览同步操作，不实际复制文件
- 输入 `n` 或直接回车: 执行实际的文件复制

干跑模式适用于：
- 首次同步前预览操作
- 验证同步计划是否正确
- 检查磁盘空间是否充足

---

## 资源类型

### 支持的资源类型

| 类型 | 扩展名 | 示例 |
|------|--------|------|
| 图片 | `.png`, `.jpg`, `.jpeg`, `.webp` | `bg_room.png` |
| 音频 | `.mp3`, `.wav`, `.ogg`, `.m4a` | `bgm_main.mp3` |
| 视频 | `.mp4`, `.webm`, `.ogv` | `opening.mp4` |

### 资源命名规范

建议使用以下命名规范：

**背景图片**:
```
bg_<场景名>.png
例: bg_room.png, bg_street.png
```

**角色立绘**:
```
char_<角色名>_<表情>.png
例: char_alice_happy.png, char_bob_sad.png
```

**背景音乐**:
```
bgm_<名称>.mp3
例: bgm_main.mp3, bgm_battle.mp3
```

**音效**:
```
sfx_<名称>.wav
例: sfx_door.wav, sfx_footstep.wav
```

**语音**:
```
voice_<编号>.mp3
例: voice_001.mp3, voice_002.mp3
```

---

## 资源库组织

### 推荐的资源库结构

```
resource_library/
├── images/
│   ├── backgrounds/
│   │   ├── bg_room.png
│   │   └── bg_street.png
│   ├── characters/
│   │   ├── alice/
│   │   │   ├── happy.png
│   │   │   └── sad.png
│   │   └── bob/
│   │       ├── normal.png
│   │       └── surprised.png
│   └── events/
│       └── cg_001.png
├── audio/
│   ├── bgm/
│   │   ├── main.mp3
│   │   └── battle.mp3
│   ├── sfx/
│   │   ├── door.wav
│   │   └── footstep.wav
│   └── voice/
│       ├── 001.mp3
│       └── 002.mp3
└── video/
    └── opening.mp4
```

### 资源库最佳实践

1. **分类存储**: 按类型和用途组织资源
2. **统一命名**: 使用一致的命名规范
3. **版本控制**: 使用 Git LFS 管理大文件
4. **文档说明**: 为每个资源添加说明文档

---

## 工作流程

### 完整的资源管理流程

1. **编写脚本** - 在 Excel 中引用资源
2. **验证资源** - 运行 `py validate_resources.py`
3. **查看报告** - 检查 `output/validation_reports/` 中的报告
4. **同步资源** - 运行 `py sync_resources.py`
5. **确认同步** - 根据提示选择是否执行同步
6. **选择模式** - 选择正常模式或干跑模式
7. **重新验证** - 再次运行验证确认资源完整
8. **生成脚本** - 运行 `py generate_scenario.py`

---

## GUI 资源管理

GUI 提供了更友好的资源管理界面。

### 使用 GUI 验证资源

1. 启动 GUI: `py run_gui.py`
2. 切换到"资源管理"标签页
3. 点击"验证资源"按钮
4. 查看验证结果

### 使用 GUI 同步资源

1. 在"资源管理"标签页
2. 点击"同步资源"按钮
3. 查看同步计划
4. 确认并执行同步

---

## 故障排除

### 验证报告为空？

1. 确认 Excel 文件在 `input/` 目录
2. 确认 `project_dirs` 配置正确
3. 检查 Excel 中是否引用了资源

### 同步找不到文件？

1. 确认资源库目录配置正确（`source_dirs`）
2. 检查资源文件名是否完全匹配（包括扩展名）
3. 确认资源文件在资源库中存在
4. 检查文件名大小写是否一致

### 同步失败？

1. 检查目标目录是否有写入权限
2. 确认磁盘空间充足
3. 查看 `logs/scenario_tool.log` 了解详细错误
4. 确认源文件和目标文件路径都正确

### 未找到验证报告？

确保先运行 `py validate_resources.py` 生成验证报告。同步工具依赖验证报告来确定需要同步的文件。

---

## 高级功能

### 自定义资源类型

编辑脚本，添加新的资源类型：

**validate_resources.py**:
```python
project_dirs = {
    "图片": Path("project/images"),
    "音频": Path("project/audio"),
    "视频": Path("project/video"),
    "字体": Path("project/fonts"),  # 新增
}
```

**sync_resources.py**:
```python
source_dirs = {
    "图片": Path("resource_library/images"),
    "音频": Path("resource_library/audio"),
    "视频": Path("resource_library/video"),
    "字体": Path("resource_library/fonts"),  # 新增
}
```

同时需要在 `ResourceSyncer` 类中添加对应的扩展名映射（第29-33行）。

### 批量处理多个项目

可以修改脚本循环处理多个项目的资源验证和同步。

---

## 最佳实践

### 1. 定期验证

在每次重大修改后运行资源验证：
```bash
py validate_resources.py
```

### 2. 保持资源库更新

及时将新资源添加到资源库，保持资源库的完整性。

### 3. 使用版本控制

将资源库纳入版本控制（使用 Git LFS 管理大文件）：
```bash
git lfs track "*.png"
git lfs track "*.mp3"
git lfs track "*.mp4"
```

### 4. 文档化资源

为每个资源添加说明，记录用途和来源：
```
resource_library/
├── README.md          # 资源库说明
├── images/
│   └── README.md      # 图片资源说明
└── audio/
    └── README.md      # 音频资源说明
```

### 5. 备份资源

定期备份资源库到云存储或外部硬盘。

### 6. 先干跑再执行

首次同步时，建议先使用干跑模式预览操作，确认无误后再执行实际同步。

---

## 下一步

- [配置说明](configuration.md) - 配置资源路径
- [快速开始](getting-started.md) - 开始使用工具
- [常见问题](faq.md) - 资源管理相关问题

---

## 相关文件

- `validate_resources.py` - 资源验证脚本
- `sync_resources.py` - 资源同步脚本
- `output/validation_reports/` - 验证报告目录
- `logs/scenario_tool.log` - 日志文件
