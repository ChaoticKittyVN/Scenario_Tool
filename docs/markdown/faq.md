# 常见问题

本文档收集了使用 Scenario Tool 时的常见问题和解决方案。

## 安装和配置

### Q: 如何安装依赖？

**A**: 使用以下命令安装：

```bash
# 生产环境
pip install -r requirements.txt

# 开发环境
pip install -r requirements-dev.txt
```

### Q: 如何切换引擎？

**A**: 编辑 `config.yaml`，修改 `engine_type`：

```yaml
engine:
  engine_type: "renpy"  # 或 "naninovel"
```

### Q: 配置文件在哪里？

**A**: 主配置文件是项目根目录的 `config.yaml`。

---

## 脚本生成

### Q: 生成的脚本在哪里？

**A**: 在 `output/` 目录中，文件扩展名根据引擎自动确定：
- Ren'Py: `.rpy`
- Naninovel: `.nani`

### Q: 为什么生成的脚本为空？

**A**: 检查以下几点：
1. Excel 中是否有 "END" 标记
2. `Ignore` 列是否标记了所有行
3. 查看 `logs/scenario_tool.log` 了解详细错误
4. 确认 Excel 文件格式正确

### Q: 如何查看详细日志？

**A**: 查看 `logs/scenario_tool.log` 文件，包含详细的执行信息。

### Q: 找不到 Excel 文件？

**A**: 确保：
1. Excel 文件在 `input/` 目录
2. 文件扩展名是 `.xlsx` 或 `.xls`
3. 文件名不以 `~` 开头（临时文件会被跳过）

### Q: 如何处理特殊字符？

**A**: 特殊字符会被自动处理。如果遇到问题，可以在参数映射中手动指定翻译。

---

## 参数映射

### Q: 如何添加新的参数映射？

**A**:
1. 编辑对应引擎的参数文件（`param_config/param_data_renpy.xlsx` 或 `param_config/param_data_naninovel.xlsx`）
2. 运行 `py update_param.py` 自动生成参数映射
3. 重新运行 `py generate_scenario.py` 生成脚本

### Q: 参数映射未生效？

**A**:
1. 确认运行了 `py update_param.py`
2. 检查 `param_config/param_mappings.py` 是否已更新
3. 重新运行 `py generate_scenario.py`

### Q: 参数表未更新？

**A**:
1. 确认 Excel 文件在 `input/` 目录
2. 确认 Excel 文件包含"参数表"工作表
3. 检查 `logs/scenario_tool.log` 查看错误信息

### Q: 如何使用差分参数？

**A**:
1. 编辑 `param_config/varient_data.xlsx`
2. 每个工作表代表一个角色
3. 运行 `py update_param.py` 生成映射

---

## 资源管理

### Q: 资源验证报告在哪里？

**A**: 在 `output/validation_reports/` 目录中。

### Q: 如何验证资源完整性？

**A**: 运行 `py validate_resources.py`，查看生成的验证报告。

### Q: 如何同步缺失的资源？

**A**:
1. 先运行 `py validate_resources.py` 生成验证报告
2. 运行 `py sync_resources.py`
3. 根据提示选择是否执行同步

### Q: 同步找不到文件？

**A**:
1. 确认资源库目录配置正确（`source_dirs`）
2. 检查资源文件名是否完全匹配（包括扩展名）
3. 确认资源文件在资源库中存在
4. 检查文件名大小写是否一致

### Q: 验证报告为空？

**A**:
1. 确认 Excel 文件在 `input/` 目录
2. 确认 `project_dirs` 配置正确
3. 检查 Excel 中是否引用了资源

---

## GUI 使用

### Q: 如何启动 GUI？

**A**: 运行 `py run_gui.py`

### Q: GUI 无法启动？

**A**:
1. 确认安装了 PySide6：`pip install PySide6`
2. 检查是否有错误信息
3. 查看 `logs/scenario_tool.log`

### Q: GUI 中如何切换引擎？

**A**: 在"默认配置"标签页中选择引擎类型。

---

## 测试

### Q: 如何运行测试？

**A**:
```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/core/test_param_translator.py -v
```

### Q: 如何查看测试覆盖率？

**A**:
```bash
pytest --cov=. --cov-report=html
```

然后打开 `htmlcov/index.html` 查看报告。

### Q: 测试失败怎么办？

**A**:
1. 查看详细错误信息：`pytest tests/ -v`
2. 运行单个失败的测试：`pytest tests/core/test_xxx.py::test_yyy -v`
3. 使用 `--pdb` 进入调试器：`pytest tests/ --pdb`

---

## 开发

### Q: 如何添加新引擎？

**A**: 参考 [开发指南 - 添加新引擎](development.md#添加新引擎)

### Q: 如何添加新生成器？

**A**: 参考 [开发指南 - 添加新生成器](development.md#添加新生成器)

### Q: 如何调试代码？

**A**:
1. 使用日志：`from core.logger import get_logger`
2. 使用 pdb：`import pdb; pdb.set_trace()`
3. 查看日志文件：`logs/scenario_tool.log`

### Q: 代码风格规范是什么？

**A**: 遵循 PEP 8 规范。

---

## 错误处理

### Q: 遇到 "ModuleNotFoundError" 错误？

**A**:
1. 确认安装了所有依赖：`pip install -r requirements.txt`
2. 确认 Python 路径正确
3. 尝试重新安装依赖

### Q: 遇到 "FileNotFoundError" 错误？

**A**:
1. 检查文件路径是否正确
2. 确认文件确实存在
3. 检查文件权限

### Q: 遇到 "PermissionError" 错误？

**A**:
1. 确认有文件写入权限
2. 关闭正在使用该文件的程序（如 Excel）
3. 以管理员权限运行

### Q: 遇到 "UnicodeDecodeError" 错误？

**A**:
1. 确认文件编码为 UTF-8
2. 检查文件是否包含特殊字符
3. 尝试重新保存文件为 UTF-8 编码

### Q: Excel 文件无法读取？

**A**:
1. 确认文件格式正确（`.xlsx` 或 `.xls`）
2. 确认文件未损坏
3. 尝试用 Excel 打开并重新保存
4. 检查是否安装了 openpyxl：`pip install openpyxl`

---

## 性能

### Q: 处理速度慢怎么办？

**A**:
1. 减少 Excel 文件大小
2. 关闭不必要的日志输出
3. 使用批处理模式
4. 考虑升级硬件

### Q: 内存占用过高？

**A**:
1. 分批处理大文件
2. 减少同时处理的文件数量
3. 关闭其他占用内存的程序

---

## 兼容性

### Q: 支持哪些 Python 版本？

**A**: 推荐使用 Python 3.11 或更高版本。

### Q: 支持哪些操作系统？

**A**: 支持 Windows、Linux 和 macOS。

### Q: 支持哪些 Excel 版本？

**A**: 支持 Excel 2007 及更高版本（`.xlsx` 格式）。

---

## 其他

### Q: 如何报告 Bug？

**A**:
1. 在 GitHub 上提交 Issue
2. 提供详细的错误信息
3. 包含复现步骤
4. 附上相关日志

### Q: 如何贡献代码？

**A**: 参考 [开发指南](development.md) 了解详细流程。

### Q: 如何获取帮助？

**A**:
1. 查看文档
2. 搜索已有的 Issue
3. 提交新的 Issue
4. 查看日志文件

### Q: 项目许可证是什么？

**A**: 与原项目保持一致。

### Q: 如何更新工具？

**A**:
```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

### Q: 如何备份数据？

**A**:
1. 备份 `input/` 目录（Excel 文件）
2. 备份 `param_config/` 目录（参数映射）
3. 备份 `config.yaml`（配置文件）
4. 使用版本控制（Git）

---

## 相关文档

- [快速开始](getting-started.md) - 开始使用工具
- [配置说明](configuration.md) - 配置选项
- [参数映射](param-mapping.md) - 参数映射管理
- [资源管理](resource-management.md) - 资源验证和同步
- [测试指南](testing.md) - 运行和编写测试
- [开发指南](development.md) - 贡献代码
- [架构设计](architecture.md) - 项目架构

---

## 找不到答案？

如果以上内容没有解决你的问题：

1. **查看日志**: `logs/scenario_tool.log`
2. **搜索 Issue**: 在 GitHub 上搜索类似问题
3. **提交 Issue**: 提供详细信息和复现步骤
4. **查看源代码**: 代码中有详细的注释

---

**最后更新**: 2025-11-23
