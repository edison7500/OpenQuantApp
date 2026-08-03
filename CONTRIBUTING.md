# Contributing to OpenQuantApp

感谢你愿意为 OpenQuantApp 做贡献。Bug 修复、数据兼容性改进、测试、文档和
范围清晰的新功能都很受欢迎。

## 开始之前

- 先搜索现有 Issue 和 Pull Request，避免重复工作。
- Bug 修复、测试和小型文档改进可以直接提交 Pull Request。
- 涉及 FastAPI、任务队列、前端替换、存储结构或大范围重构时，请先创建
  Issue，说明目标、边界和迁移方案。
- 安全问题不要提交公开 Issue，请按照 [SECURITY.md](SECURITY.md) 私下报告。

## 开发环境

项目要求 Python 3.12+，并使用 `uv` 管理依赖与虚拟环境。

```bash
git clone https://github.com/edison7500/OpenQuantApp.git
cd OpenQuantApp
uv sync
```

按照 [README.md](README.md) 创建本地 `.streamlit/secrets.toml`，只配置当前开发
所需的服务。不要提交 API Key、Token、个人数据库、行情缓存或其他敏感数据。

启动应用：

```bash
uv run streamlit run app.py
```

## 开发流程

1. Fork 仓库并从最新主分支创建短生命周期分支，例如 `feature/...`、`fix/...`
   或 `docs/...`。
2. 保持修改聚焦；不要在同一个 Pull Request 中混入无关格式化或重构。
3. 为配置解析、数据转换、分析逻辑和缺陷修复补充相应测试。
4. 更新受影响的文档和示例配置，但不要加入真实凭据。
5. 完成下方检查后提交 Pull Request。

## 代码约定

- 新增项目逻辑应使用类型注解，并遵循现有模块职责。
- 将数据源和 LLM Provider 差异隔离在 manager、provider 或 factory 中。
- 核心分析逻辑应尽量独立于 Streamlit Session State，以便未来复用于 FastAPI。
- 修改数据库或 ArcticDB 结构时必须考虑已有数据兼容性；关系数据库变更使用
  Alembic migration。
- LLM 输出应区分事实与推断，同时呈现正反证据、置信度和数据限制，避免虚构
  精确数字或使用煽动性表述。

## 本地检查

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

开发时可以先运行与修改相关的测试，但提交前应尽量完成全量检查。如果某项
检查因环境或外部服务不可用而未运行，请在 Pull Request 中明确说明。

## Pull Request 检查清单

- [ ] 变更解决了一个明确的问题，且范围保持聚焦。
- [ ] 新行为已有测试覆盖，或已说明无法测试的原因。
- [ ] Pytest 与 Ruff 检查通过，或已记录未通过/未运行的项目。
- [ ] 用户可见行为、配置或命令变化已更新文档。
- [ ] 没有提交密钥、Token、个人数据、缓存或生成的大型数据文件。
- [ ] 对数据库、配置和公共接口的兼容性影响已有说明。

Pull Request 描述应包含修改动机、主要行为变化、验证方式，以及必要的界面截图
或日志。日志必须先移除凭据、请求头和个人信息。

## Bug 报告

请尽量提供：

- OpenQuantApp 版本或 commit；
- 操作系统、Python 版本和运行方式（本地或 Docker）；
- 最小复现步骤、预期行为和实际行为；
- 已脱敏的错误日志；
- 涉及的数据源、资产类型、周期和 LLM Provider。

市场数据误差、Provider 故障或 LLM 结果问题也可以报告，但请提供可核验的原始
数据来源和时间范围。

## 许可证

向本项目提交代码或文档，即表示你同意贡献内容按照项目的
[MIT License](LICENSE) 发布，并确认你有权提交这些内容。
