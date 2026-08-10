# -*- coding: utf-8 -*-

import concurrent.futures
from PySide6.QtCore import Qt, QEvent, QTimer
from PySide6.QtWidgets import (
    QWidget,
    QStackedWidget,
    QHBoxLayout,
    QMainWindow,
    QVBoxLayout,
    QGridLayout,
    QFrame,
    QApplication,
)
from PySide6.QtGui import QPixmap, QIcon, QColor
from qfluentwidgets import (
    CardWidget,
    TitleLabel,
    ImageLabel,
    StrongBodyLabel,
    SegmentedWidget,
    InfoLevel,
    FluentIcon,
    PrimaryToolButton,
    setTheme,
    Theme,
    InfoBarIcon,
    CaptionLabel,
    InfoBar,
    InfoBarPosition,
    InfoBadgePosition,
)

from app.common.test_monitor import TestMonitor
from app.common.config import cfg
from app.view.settings_window import SettingsWindow
from app.common.signal_bus import signalBus
from app.components.system_tray_icon import SystemTrayIcon
from app.common.upload_task import process_upload
from app.common.logger import Logger
from app.components.auto_restart import AutoRestartManager
from app.components.ui_helpers import setInfoBadge
from app.components.raw_data_converter import raw_manager
from app.components.ftp_server import ftp_server_manager
from app.common.station import (
    get_station_config,
    validate_station_config,
    get_station_ui_classes,
)

from app.view.chip_label import ChipLabel, ChipType
import time
import threading
import app.common.sfc_server as sfc_server
from app.common.Submit_Csv import csv_writer, _batch_save_to_csv_smb
from app.view.query_window import QueryWindow
from app.components.smb_mount import smb_mount_service
from datetime import datetime
from version import get_version, get_name, get_version_tuple, get_description


logger = Logger("Application")


class CustomEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, value):
        super().__init__(CustomEvent.EVENT_TYPE)
        self.value = value


class FluentMainWindow(QMainWindow):
    """使用 Fluent Design 和无边框窗口的主窗口"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._setup_window()
        self._create_widgets()
        self._setup_tables()
        self._setup_layouts()
        self._setup_logo()
        self._setup_services()
        self._connect_signals()
        self._init_ui_data()

        self.settings_window = None  # 设置窗口实例
        self.query_window = None  # 查询窗口实例
        self.systemTrayIcon = SystemTrayIcon(self)
        self.auto_restart_manager = AutoRestartManager(self)

        self.module_alive_checker_thread = threading.Thread(
            target=self.check_module_availability, daemon=True
        )
        self.onInitFinished()

    def _setup_window(self):
        """设置窗口基本属性"""

        # self.setTitleBar(StandardTitleBar(self))  # FramelessMainWindow 时启用
        self.setWindowTitle(f"{get_name()}_{get_version()}")
        self.setWindowIcon(QIcon(":/app/images/logo.png"))
        self.resize(900, 750)
        self.setMinimumSize(800, 650)
        QApplication.setQuitOnLastWindowClosed(False)

        # 设置主题
        setTheme(Theme.AUTO)

        self.show()

    def _create_widgets(self):
        """创建所有控件"""
        # 中心控件（FramelessMainWindow 使用 setCentralWidget）
        self.central_widget = QWidget()
        self.central_widget.setObjectName("centralWidget")
        self.setCentralWidget(self.central_widget)
        # self.setContentsMargins(-1, self.titleBar.height(), -1, -1) # FramelessMainWindow 时启用

        # 头部卡片组件
        self.header_card = CardWidget(self.central_widget)
        self.app_title = TitleLabel(get_description())
        self.logo_label = ImageLabel()

        self.chip_layout = QGridLayout()
        self.chip_layout.setHorizontalSpacing(1)
        self.chip_layout.setVerticalSpacing(1)
        self.sfc_chip = ChipLabel("SFC", ChipType.SUCCESS)
        self.chip_layout.addWidget(self.sfc_chip, 0, 0)
        # self.ftp_chip = ChipLabel("FTP Server", ChipType.SUCCESS)
        # self.raw_chip = ChipLabel("Raw Data", ChipType.SUCCESS)

        # 信息标签

        self.line_title = CaptionLabel("线别名称")
        self.line_label = StrongBodyLabel("未设置")

        self.product_title = CaptionLabel("产品名称")
        self.product_label = StrongBodyLabel("SMT Data Collector")

        self.station_title = CaptionLabel("工站名称")
        self.station_label = StrongBodyLabel("未设置")

        self.op_id_title = CaptionLabel("操作员 ID")
        self.op_id_label = StrongBodyLabel("未登录")

        self.setting_button = PrimaryToolButton(FluentIcon.SETTING)

        self.query_button = PrimaryToolButton(FluentIcon.SEARCH, self)
        self.query_button.setToolTip("数据查询")

        # 内容卡片组件
        self.content_card = CardWidget(self.central_widget)
        self.pivot = SegmentedWidget(self.content_card)
        self.stacked_widget = QStackedWidget(self.content_card)

    def _setup_tables(self):
        """根据工站配置动态创建表格组件"""
        station_code = cfg.get(cfg.station_code)

        # 验证工站配置
        if not validate_station_config(station_code):
            logger.error(f"工站配置无效或不存在: {station_code}")
            raise ValueError(f"工站代码 '{station_code}' 的配置无效或不存在")

        try:
            status_table_class, content_table_class = get_station_ui_classes(
                station_code
            )
            logger.debug(
                f"加载工站 {station_code} 的 UI 组件: {status_table_class.__name__}, {content_table_class.__name__}"
            )

            self.status_table = status_table_class()
            self.content_table = content_table_class()
        except (ValueError, TypeError) as e:
            logger.error(f"解析工站 {station_code} 的 UI 配置失败: {e}")
            raise ValueError(f"工站 '{station_code}' 的 UI 配置格式错误") from e

    def _setup_layouts(self):
        """设置布局"""
        # 中心控件布局（顶部留出32px给标题栏）
        main_layout = QVBoxLayout(self.central_widget)
        # main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 头部卡片布局
        header_layout = QVBoxLayout(self.header_card)
        header_layout.setContentsMargins(10, -1, 10, -1)
        header_layout.setSpacing(15)

        # 标题行
        title_layout = QHBoxLayout()
        title_layout.addWidget(self.app_title)
        title_layout.addStretch()
        title_layout.addLayout(self.chip_layout)
        title_layout.addStretch()
        title_layout.addWidget(self.logo_label)
        header_layout.addLayout(title_layout)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFixedHeight(1)
        header_layout.addWidget(separator)

        # 信息网格
        info_grid = QGridLayout()
        info_grid.setHorizontalSpacing(30)
        info_grid.setVerticalSpacing(12)

        info_grid.addWidget(self.product_title, 0, 0)
        info_grid.addWidget(self.product_label, 1, 0)

        info_grid.addWidget(self.line_title, 0, 1)
        info_grid.addWidget(self.line_label, 1, 1)

        info_grid.addWidget(self.station_title, 0, 2)
        info_grid.addWidget(self.station_label, 1, 2)

        info_grid.addWidget(self.op_id_title, 0, 3)
        info_grid.addWidget(self.op_id_label, 1, 3)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)
        button_layout.addWidget(self.query_button)
        button_layout.addWidget(self.setting_button)

        info_grid.addLayout(
            button_layout, 0, 4, 2, 1, Qt.AlignHCenter | Qt.AlignVCenter
        )

        header_layout.addLayout(info_grid)
        main_layout.addWidget(self.header_card)

        # 内容卡片布局
        content_layout = QVBoxLayout(self.content_card)
        content_layout.setContentsMargins(10, -1, 10, -1)
        content_layout.setSpacing(10)

        content_layout.addWidget(self.pivot, 0, Qt.AlignHCenter)
        content_layout.addWidget(self.stacked_widget)
        main_layout.addWidget(self.content_card)

        # 状态视图
        status_view = QWidget()
        status_view.setObjectName("status_view")
        status_layout = QVBoxLayout(status_view)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.addWidget(self.status_table)
        self.stacked_widget.addWidget(status_view)

        # 内容视图
        content_view = QWidget()
        content_view.setObjectName("content_view")
        content_view_layout = QVBoxLayout(content_view)
        content_view_layout.setContentsMargins(0, 0, 0, 0)
        content_view_layout.addWidget(self.content_table)
        self.stacked_widget.addWidget(content_view)

        # 设置 Pivot 选项卡 - 不使用 onClick，使用信号连接
        self.pivot.addItem(
            routeKey="status_view",
            text="状态监控",
            onClick=lambda: self.stacked_widget.setCurrentIndex(0),
        )
        self.pivot.addItem(
            routeKey="content_view",
            text="详细内容",
            onClick=lambda: self.stacked_widget.setCurrentIndex(1),
        )

        self.pivot.setCurrentItem("status_view")

    def _setup_logo(self):
        logger.debug("Setup Logo")
        logo = QPixmap(":app/images/logo_foxlink_b.png")
        if logo.isNull():
            logger.error("无法加载图片.")
            return

        self.logo_label.setPixmap(logo)

    def _setup_services(self):
        """设置后台服务（如服务器线程）"""
        self.test_monitor = TestMonitor()

        # 创建上传线程池
        self.upload_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=8, thread_name_prefix="UploadWorker"
        )
        # 用于跟踪所有提交的上传任务
        self.upload_futures = []

    def _connect_signals(self):
        """连接信号"""
        signalBus.appMessageSig.connect(self.onAppMessage)

        self.setting_button.clicked.connect(self.on_setting_clicked)
        self.query_button.clicked.connect(self.on_query_clicked)

        # InfoBar
        signalBus.infoBarSig.connect(self.show_info_bar)

        # 信息栏信号
        cfg.line_name.valueChanged.connect(
            lambda: self.line_label.setText(cfg.get(cfg.line_name))
        )
        cfg.op_id.valueChanged.connect(
            lambda: self.op_id_label.setText(cfg.get(cfg.op_id))
        )
        cfg.station_code.valueChanged.connect(
            lambda: self.station_label.setText(cfg.get(cfg.station_code))
        )

        signalBus.sfc_status_signal.connect(self.sfc_chip.setType)

        signalBus.appErrorSig.connect(self.show_info_bar)

        # Add Status Row Signal
        signalBus.addStatusRowSig.connect(self.add_status_row)

        signalBus.moduleUpdateSignal.connect(self.update_module_status)

        # signalBus.update_chip_status_signal.connect(self.update_chip_show)

    def _init_ui_data(self):
        """初始化UI数据"""

        self.line_label.setText(cfg.get(cfg.line_name))
        self.station_label.setText(cfg.get(cfg.station_code))
        self.op_id_label.setText(cfg.get(cfg.op_id))

        self.sfc_chip.setType(ChipType.WARNING)
        self._load_history_data()

    def onInitFinished(self):
        """初始化完成后的回调"""
        logger.info("UI Initialization Finished")
        self.systemTrayIcon.show()
        self.start_background_services()

    def start_background_services(self):
        """启动后台服务"""
        # sfc_server.run_server_in_thread()
        raw_manager.start()
        ftp_server_manager.start()
        smb_mount_service.start()
        # self.module_alive_checker_thread.start()

        try:
            self.test_monitor.check_monitor_path()
        except (ValueError, FileNotFoundError) as e:
            logger.error(f"Monitor path configuration error: {e}")
            self.show_info_bar(
                "错误", f"Log 路径配置错误: {e}", InfoBarIcon.ERROR, duration=30000
            )
            setInfoBadge(self.setting_button, "!", level=InfoLevel.ERROR)
            return

        logger.info("Starting Background Services")
        try:
            self.test_monitor._setup_observer()
            self.test_monitor._setup_threads()
            self.test_monitor.start()
        except Exception as e:
            logger.error(f"Failed to start Test Monitor: {e}")
            self.show_info_bar(
                "错误", f"无法启动测试监控服务: {e}", InfoBarIcon.ERROR, duration=30000
            )
            self.show_info_bar(
                "错误",
                f"无法启动测试监控服务: {e}",
                InfoBarIcon.ERROR,
                position=InfoBarPosition.BOTTOM,
                duration=30000,
            )

    def onAppMessage(self, message: str):
        if message == "show":
            if self.windowState() & Qt.WindowMinimized:
                self.showNormal()
            else:
                self.show()
                self.raise_()
        elif message == "restart":
            self.show_info_bar(
                "提示", "应用程序正在重启...", InfoBarIcon.WARNING, duration=10000
            )
            self.onExit()
            QTimer.singleShot(1000, self.auto_restart_manager.restartApplication)
        else:
            # TODO: parse command line args
            self.show()

    def show_info_bar(
        self,
        title: str,
        content: str,
        icon: InfoBarIcon,
        duration_or_position=None,
        duration: int = None,
    ):
        """
        显示信息栏

        兼容两种调用方式:
        1. show_info_bar(title, content, icon, duration) - 从信号调用
        2. show_info_bar(title, content, icon, position, duration) - 直接调用
        """
        # 判断第4个参数是 duration 还是 position
        if duration_or_position is None:
            position = InfoBarPosition.TOP
            final_duration = 2000
        elif isinstance(duration_or_position, int):
            # 第4个参数是 int,说明是 duration (从信号调用)
            position = InfoBarPosition.TOP
            final_duration = duration_or_position
        else:
            # 第4个参数是 InfoBarPosition
            position = duration_or_position
            final_duration = duration if duration is not None else 2000

        _info_bar = InfoBar(
            icon=icon,
            title=title,
            content=content,
            orient=Qt.Horizontal,
            isClosable=True,
            position=position,
            duration=final_duration,
            parent=self,
        )
        _info_bar.show()

    def on_setting_clicked(self):
        """设置按钮点击事件"""
        # 如果设置窗口已存在且可见，则激活它
        if self.settings_window is not None and self.settings_window.isVisible():
            self.settings_window.raise_()
            self.settings_window.activateWindow()
            return
        # 创建新的设置窗口
        self.settings_window = SettingsWindow(self)
        self.settings_window.show()

    def on_query_clicked(self):
        """查询按钮点击事件"""
        # 如果查询窗口已存在且可见，则激活它
        if self.query_window is not None and self.query_window.isVisible():
            self.query_window.raise_()
            self.query_window.activateWindow()
            return

        # 创建新的查询窗口
        self.query_window = QueryWindow(self)
        self.query_window.show()

    def add_status_row(self, model):
        """向 Status 表格添加一行数据"""
        self.status_table.add_row_from_model(model)

        # 提交上传任务到线程池
        future = self.upload_pool.submit(process_upload, model)
        self.upload_futures.append(future)
        # 添加回调，以便在上传完成时更新UI
        future.add_done_callback(self.upload_done_callback)

    def add_content_row(self, model):
        """向 Content 表格添加一行数据"""
        self.content_table.add_row_from_model(model)

    def _load_history_data(self):
        """加载历史数据到Content表格"""
        try:
            station_code = cfg.get(cfg.station_code)
            logger.info(f"开始加载历史数据，工站代码: {station_code}")

            # 根据工站代码选择对应的数据模型
            if station_code == "110":  # AOI/SPI站别
                from app.common.database import AOI_SPI

                model_class = AOI_SPI
            elif int(station_code) in (109, 122):  # 炉温站别
                from app.common.database import ReflowOven

                model_class = ReflowOven
            else:
                logger.warning(f"未知的工站代码: {station_code}，跳过加载历史数据")
                return

            # 查询最近100条记录，按时间倒序
            records = list(
                model_class.select().order_by(model_class.record_time.desc()).limit(100)
            )

            record_count = len(records)

            # 反转列表，从旧到新添加，由于add_row_from_model在第0行插入，最终最新的会在顶部
            for record in reversed(records):
                self.content_table.add_row_from_model(record)

            logger.info(f"历史数据加载完成，共加载 {record_count} 条记录")

        except Exception as e:
            logger.error(f"加载历史数据失败: {e}")
            import traceback

            logger.error(traceback.format_exc())

    def clear_tables(self):
        """清空所有表格"""
        self.status_table.clear()
        self.content_table.clear()

    def upload_done_callback(self, future):
        """上传完成后的回调函数"""
        try:
            # 从Future中获取结果
            result = future.result()
            # 在主线程中更新UI - 使用Qt的事件循环确保UI更新是线程安全的
            QApplication.postEvent(self, CustomEvent(result))
            # 从跟踪列表中移除已完成的future
            if future in self.upload_futures:
                self.upload_futures.remove(future)
        except Exception as e:
            logger.error(f"处理上传结果时出错: {e}")

    def on_upload_finished(self, result):
        filename = datetime.now().strftime(
            f"smt-data-collector_{cfg.get(cfg.station_code)}_{cfg.get(cfg.type)}_%Y%m%d.csv"
        )
        try:
            logger.info(f"on_upload_finished: {result.serial_number}")
            csv_writer.save_csv_data(result, filename)
            _batch_save_to_csv_smb(result, filename)

            self.add_content_row(result)
        except Exception as e:
            logger.error(f"Error in upload_to_sfc: {e}")

    def update_module_status(self, module_name, is_available):
        """更新模块状态标签"""
        if module_name == "FTP":
            self.ftp_chip.setType(ChipType.ONLINE if is_available else ChipType.OFFLINE)
        elif module_name == "Raw":
            self.raw_chip.setType(ChipType.ONLINE if is_available else ChipType.OFFLINE)

    def check_module_availability(self):
        """检查各模块可用性，更新状态标签"""
        time.sleep(2)  # 等待界面初始化完成
        while True:
            try:
                # 检查 FTP 服务器状态
                ftp_mode_enabled = cfg.get(cfg.ftp_mode)
                if ftp_mode_enabled:
                    ftp_available = ftp_server_manager.is_running
                    signalBus.moduleUpdateSignal.emit("FTP", ftp_available)
                # 检查 Raw Data 上传状态
                raw_mode_enabled = cfg.get(cfg.raw_upload_mode)
                if raw_mode_enabled:
                    raw_available = raw_manager.is_running
                    signalBus.moduleUpdateSignal.emit("Raw", raw_available)
            except Exception as e:
                logger.error(f"Module availability check error: {e}")

            time.sleep(6)

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        event.ignore()
        self.hide()

    # 重写事件处理函数
    def event(self, event):
        if event.type() == CustomEvent.EVENT_TYPE:
            # 处理自定义事件
            self.on_upload_finished(event.value)
            return True
        return super().event(event)

    def onExit(self):
        """exit main window"""

        # 停止后台服务
        self.systemTrayIcon.hide()
        raw_manager.stop()
        ftp_server_manager.stop()
        self.test_monitor.stop()
        smb_mount_service.stop()
        # 关闭线程池
        self.upload_pool.shutdown(wait=False)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    app.setApplicationName("SMT Data Collector")
    app.setOrganizationName("Foxlink")

    # 创建主窗口
    window = FluentMainWindow()
    window.show()

    # 添加多条测试数据到状态表
    test_data = [
        ("2025-11-19 09:28:26", "G5Y09040800306318020435", "PASS", "已上传"),
        ("2025-11-19 09:30:15", "G5Y09040800306318020436", "FAIL", "已上传"),
        ("2025-11-19 09:32:08", "G5Y09040800306318020437", "PASS", "已上传"),
        ("2025-11-19 09:35:42", "G5Y09040800306318020438", "SKIP", "已上传"),
        ("2025-11-19 09:37:12", "G5Y09040800306318020439", "PASS", "已上传"),
    ]

    for data in test_data:
        window.add_status_row(*data)

    # 添加详细内容数据
    content_data = [
        {
            "time": "2025-11-19 09:28:26",
            "serial": "G5Y09040800306318020435",
            "product": "0E85-T-01S1-P2-01(03)",
            "station": "AOI-106",
            "result": "PASS",
            "flags": "0;0;1;0;",
            "bot_or_top": "T",
            "items": "150",
            "detail": "",
            "note": "",
        },
        {
            "time": "2025-11-19 09:30:15",
            "serial": "G5Y09040800306318020436",
            "product": "0E85-T-01S1-P2-01(03)",
            "station": "AOI-106",
            "result": "FAIL",
            "flags": "0;0;0;1;",
            "bot_or_top": "T",
            "items": "150",
            "detail": "焊接不良",
            "note": "需要返修",
        },
    ]

    for data in content_data:
        window.add_content_row(data)

    # 打印统计信息
    stats = window.get_statistics()
    print(
        f"统计信息: 总数={stats['total']}, 通过={stats['pass']}, 失败={stats['fail']}, 跳过={stats['skip']}"
    )

    sys.exit(app.exec_())
