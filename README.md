# Moose SMT Upload Tool 总结

## 软件简介

Moose SMT Upload Tool 是一个用于 SMT 产线测试数据采集、解析、入库、上传与导出的桌面应用。

它主要服务 AOI/SPI、Reflow（回流炉）等站点，核心目标是把设备侧日志文件自动转成结构化记录，并对接 SFC 系统完成上传，同时支持本地 CSV 与 RAW 数据产出、FTP 共享与 SMB 挂载写入。

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
- pyarmor（代码保护）

## 项目模块概览

- app/common：配置、数据库模型、SFC 对接、上传任务、信号总线等核心逻辑。
- app/components：文件监听处理器、FTP/SMB、RAW 转换、系统托盘、自启与重启管理。
- app/parsers：AOI/SPI 与 Reflow 日志解析器。
- app/view：主窗口、设置页、查询页及各站点 UI 组件。

## 软件定位

该工具本质上是一个面向产线现场的数据中台客户端：

- 向下兼容不同设备日志格式。
- 向上对接 SFC 与追溯体系。
- 对现场提供可视化、可配置、可恢复的稳定上传能力。
