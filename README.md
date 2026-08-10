<p align="center">
  <img width="64" align="center" src="assets/images/logo.png" alt="logo">
</p>
<h1 align="center">smt-data-collector</h1>
<p align="center">SMT 产线测试数据采集、解析、入库与 SFC 上传桌面工具</p>

<div align="center">

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](#环境要求)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey.svg)]()

</div>

---

## 软件简介

smt-data-collector 是一个用于 SMT 产线测试数据采集、解析、入库、上传与导出的桌面应用。

它主要服务 AOI/SPI、Reflow（回流炉）等站点，核心目标是把设备侧日志文件自动转成结构化记录，并对接 SFC 系统完成上传，同时支持本地 CSV 与 RAW 数据产出、FTP 共享与 SMB 挂载写入。

## 快速开始

### 环境要求

- Python 3.8.10+
- Windows 10+ / macOS（SMB 挂载依赖系统 `mount_smbfs` / `net use`）

### 从源码运行

推荐使用 [uv](https://docs.astral.sh/uv/)（也可以使用 pip）：

```bash
# uv
uv sync
uv run python main.py

# pip
pip install -e .
python main.py
```

首次启动后：

1. 在设置页（默认密码 `123`）配置监控目录、站别、SFC 地址与账号、SMB/FTP 参数。
2. 配置保存在本地 `AppData/config.json`（已 gitignore，不会入库）；结构参考根目录 `config.example.json`。
3. 开启对应站点的文件监听后，新文件会自动解析、入库并按规则上传/导出。

> 注意：SFC / SMB / FTP 的服务器地址、账号、密码均为现场环境信息，请勿提交到仓库。

## 核心能力

1. 自动监控指定目录中的新测试文件（基于文件系统事件）。
2. 按站点类型解析日志：
	- AOI/SPI：CSV 解析、提取最后一批 panel 数据与测量值。
	- Reflow：TXT 日志解析，提取温区、斜率、峰值等工艺参数。
3. 关联 SFC：
	- 查询 panel 对应的单板 SN。
	- 根据 PASS/FAIL 结果上传记录。
	- 在线/离线模式切换。
4. 数据落地与追溯：
	- SQLite 存储完整测试记录。
	- 按模型导出 CSV（含可配置表头顺序）。
	- 生成 RAW 文件并按规则命名/搬运。
5. 文件服务能力：
	- 内置 FTP 服务共享目录。
	- 支持 SMB 自动挂载并进行远端写入。
6. 客户端能力：
	- 单实例运行与进程间消息通知。
	- 图形化状态监控、设置管理、查询窗口、系统托盘。
	- 线程池并发上传与多线程后台任务管理。

## 典型处理流程

1. 监听测试目录并捕获新文件。
2. 按站点解析原始日志为结构化数据。
3. 调用 SFC 获取/校验 SN 与站点路由信息。
4. 保存记录到 SQLite。
5. 将上传任务投递到线程池并回写上传状态。
6. 按配置输出 CSV / RAW，并通过 FTP 或 SMB 暴露/写入。
7. UI 实时刷新状态表与详细内容表。

## 技术栈

### 语言与运行环境

- Python 3.8.10+

### 桌面 UI

- PySide6（Qt for Python）
- PySide6-Fluent-Widgets / qfluentwidgets（Fluent 风格组件）

### 数据与持久化

- peewee（ORM）
- SQLite（本地数据库）
- csv / json（标准库数据落地）

### 文件监控与任务并发

- watchdog（文件系统监听）
- threading / queue / concurrent.futures（并发与任务队列）
- portalocker（跨平台单实例文件锁）

### 网络与系统集成

- urllib.request（SFC HTTP 接口调用）
- pyftpdlib（内置 FTP 服务）
- SMB 挂载（macOS: mount_smbfs；Windows: net use）

### 日志与运维

- loguru（日志管理）
- 崩溃处理与分模块日志归档（应用内实现）

### 打包与发布

- pyinstaller（应用打包）
- pyarmor（代码保护，可选）

## 项目结构

```
smt-data-collector/
├── app/
│   ├── common/       # 配置、数据库模型、SFC 对接、上传任务、信号总线等核心逻辑
│   ├── components/   # 文件监听、FTP/SMB、RAW 转换、系统托盘、自启与重启管理
│   ├── parsers/      # AOI/SPI 与 Reflow 日志解析器
│   └── view/         # 主窗口、设置页、查询页及各站点 UI 组件
├── assets/           # 图标与 Qt 资源定义（resource.qrc）
├── hooks/            # PyInstaller 打包钩子
├── tests/            # 冒烟测试
├── main.py           # 应用入口
├── resource.py       # 由 assets/resource.qrc 生成的 Qt 资源模块（pyside6-rcc）
├── pyproject.toml    # 项目元数据与依赖（单一数据源）
└── config.example.json  # 配置示例（脱敏）
```

> 修改 `assets/resource.qrc` 后，需重新生成资源模块：
> `pyside6-rcc assets/resource.qrc -o resource.py`

## 开发

```bash
# 安装开发依赖
uv sync --extra dev

# 运行测试
uv run pytest

# 代码检查
uv run ruff check .
```

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 软件定位

该工具本质上是一个面向产线现场的数据中台客户端：

- 向下兼容不同设备日志格式。
- 向上对接 SFC 与追溯体系。
- 对现场提供可视化、可配置、可恢复的稳定上传能力。

## 文档

- [变更日志](CHANGELOG.md)
- [贡献指南](CONTRIBUTING.md)
- [安全说明](SECURITY.md)

## 许可证

[Apache License 2.0](LICENSE)
