# 贡献指南

感谢您对 MESLogRelay 感兴趣！在提交贡献之前，请阅读以下指南。

## 开发环境

推荐使用 [uv](https://docs.astral.sh/uv/) 管理项目依赖：

```bash
# 克隆仓库
git clone https://github.com/Jiayu-zheng1/MESLogRelay.git
cd MESLogRelay

# 安装依赖（含开发依赖）
uv sync --extra dev

# 启动应用
uv run python main.py
```

最低 Python 版本：3.8.10（Windows 10+ / macOS）。

## 运行测试与代码检查

```bash
# 冒烟测试（版本一致性 + 核心模块可导入）
uv run pytest

# 代码检查（语法与未定义名称错误）
uv run ruff check .
```

提交前请确保以上命令全部通过。

## 分支与提交规范

- 功能开发请基于 `main` 分支创建新分支，命名建议：`feat/xxx`、`fix/xxx`。
- 提交信息使用 Conventional Commits 风格，例如：
  - `feat: 支持新的设备日志格式`
  - `fix: 修复 SFC 上传失败时状态未回写的问题`
  - `docs: 更新 README`
  - `refactor: 重构解析器，提取公共逻辑`
- 代码注释使用中文，技术术语与 API 名称保留英文。

## 提交流程

1. Fork 本仓库并创建您的分支。
2. 在本地完成修改，确保测试与 lint 通过。
3. 提交 Pull Request，并填写 [PR 模板](.github/PULL_REQUEST_TEMPLATE.md)。
4. 维护者 review 后会与您沟通或合并。

## 代码风格约定

- 本项目为 PyQt/PySide6 GUI 项目，请遵循面向对象编程逻辑组织代码。
- 新增依赖请同时更新 `pyproject.toml`（依赖单一数据源），并通过 `uv lock` 重新生成锁文件。
- 新增/修改 `assets/resource.qrc` 后，需重新生成资源模块：
  ```bash
  pyside6-rcc assets/resource.qrc -o resource.py
  ```
- 请勿提交运行时数据（`AppData/`、`*.db`、`*.log`、`*.raw`）与现场环境信息（服务器地址、账号、密码）。
