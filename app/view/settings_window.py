# -*- coding: utf-8 -*-

import os
from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QDialog,
    QApplication,
    QFileDialog,
    QGridLayout,
)
from PySide6.QtGui import QColor
from qfluentwidgets import (
    ScrollArea,
    SettingCard,
    ExpandSettingCard,
    PrimaryPushButton,
    LineEdit,
    ComboBox,
    SwitchButton,
    FluentIcon,
    InfoBarIcon,
    InfoBar,
    TitleLabel,
    InfoBarPosition,
    PasswordLineEdit,
    PushSettingCard,
    MessageBox,
    ComboBoxSettingCard,
    ExpandGroupSettingCard,
    BodyLabel,
)

from app.common.config import cfg, get_ip_options
from app.common.signal_bus import signalBus
from app.common.const import SETTINGS_PASSWORD
from app.common.station import station, get_station_config
from app.components.auto_start import AutoStartManager
from app.common.logger import Logger
from app.common.const import DEBUG

logger = Logger("SettingsWindow")


class MonitorSettingCard(ExpandGroupSettingCard):
    """监控路径设置卡片组"""

    def __init__(self, parent=None):
        super().__init__(FluentIcon.FOLDER_ADD, "监控设置", parent)

        # 在这里添加具体的点胶设置项
        # 例如:
        # self.valve_weight_card = SettingCard(
        #     FluentIcon.WEIGHT,
        #     "阀门重量",
        #     parent=self.viewWidget
        # )
        # self.viewLayout.addWidget(self.valve_weight_card)

        # 你可以根据需要添加更多的设置项


class SettingsWindow(QDialog):
    """设置窗口"""

    # 定义信号
    settingsSaved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.resize(750, 650)
        self.setMinimumSize(650, 550)
        self.setMaximumSize(800, 650)

        # 设置为模态窗口，阻止主窗口交互
        self.setWindowModality(Qt.ApplicationModal)

        # 创建主容器和布局
        self.main_layout = QVBoxLayout(self)
        # self.main_layout.setContentsMargins(-1, self.titleBar.height(), -1, -1)
        self.main_layout.setSpacing(20)

        # 标题区域（包含标题和密码验证）
        self.title_layout = QHBoxLayout()
        self.title_label = TitleLabel("设置", self)
        self.title_layout.addWidget(self.title_label)
        self.title_layout.addStretch(1)

        self.autoStartManager = AutoStartManager()

        # 密码验证区域
        self.password_widget = QWidget(self)
        self.password_layout = QHBoxLayout(self.password_widget)
        self.password_layout.setContentsMargins(0, 0, 0, 0)
        self.password_layout.setSpacing(8)

        self.password_edit = PasswordLineEdit(self.password_widget)
        self.password_edit.setPlaceholderText("请输入密码")
        self.password_edit.setFixedWidth(200)
        self.password_edit.textChanged.connect(self._verify_password)

        self.password_layout.addWidget(self.password_edit)

        self.title_layout.addWidget(self.password_widget)

        # 初始状态:禁用所有编辑控件
        self.is_unlocked = False

        # 保存原始值用于还原
        self.original_values = {}
        self.settings_saved = False

        # 创建滚动区域
        self.scroll_area = ScrollArea(self)
        self.scroll_widget = QWidget()
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(
            "QScrollArea {border: none; background-color: transparent;}"
        )

        # 设置卡片布局
        self.setting_layout = QVBoxLayout(self.scroll_widget)
        self.setting_layout.setSpacing(10)
        self.setting_layout.setContentsMargins(10, 0, 0, 10)

        # 创建设置卡片
        self._create_setting_cards()

        # 底部按钮区域
        self.button_layout = QHBoxLayout()
        self.button_layout.addStretch(1)
        self.save_button = PrimaryPushButton(FluentIcon.SAVE, "保存设置", self)
        self.save_button.setFixedWidth(120)
        self.button_layout.addWidget(self.save_button)

        # 组装布局
        self.main_layout.addLayout(self.title_layout)
        self.main_layout.addSpacing(10)
        self.main_layout.addWidget(self.scroll_area, 1)
        self.main_layout.addLayout(self.button_layout)

        # 初始禁用所有编辑控件
        self._set_editing_enabled(False)

        # 连接信号
        self.save_button.clicked.connect(self.save_settings)

        cfg.Auto_Start.valueChanged.connect(self._onAutoStartChanged)

        # 设置窗口图标
        self.setWindowIcon(FluentIcon.SETTING.icon())

    def _verify_password(self):
        """验证密码"""
        password = self.password_edit.text()
        # 这里设置密码，可以从配置文件读取或硬编码
        correct_password = SETTINGS_PASSWORD

        if password == correct_password:
            self.show_info_bar("成功", "已解锁", InfoBarIcon.SUCCESS)
            self.is_unlocked = True
            self._set_editing_enabled(True)
            self.password_widget.hide()
            # self.password_edit.clear()
        # else:
        #     self.show_info_bar("错误", "密码错误，请重试", InfoBarIcon.ERROR)
        #     self.password_edit.clear()
        #     self.password_edit.setFocus()

    def _set_editing_enabled(self, enabled: bool):
        """设置是否允许编辑"""
        self.monitor_path_card.button.setEnabled(enabled)
        self.csv_path_card.button.setEnabled(enabled)
        self.Raw_data_path_card.button.setEnabled(enabled)
        self.line_name_edit.setEnabled(enabled)
        self.station_combo.setEnabled(enabled)
        self.op_id_edit.setEnabled(enabled)
        self.uop_switch.setEnabled(enabled)
        self.ip_combo.setEnabled(enabled)
        self.sfc_url_edit.setEnabled(enabled)
        self.save_button.setEnabled(enabled)
        self.ftp_switch.setEnabled(enabled)
        self.raw_switch.setEnabled(enabled)
        self.sbm_setting_card.set_enabled(enabled)
        self.smb_switch_button.setEnabled(enabled)
        self.Auto_start_switch_button.setEnabled(enabled)

    def validate_settings(self):
        """验证必要设置并显示错误状态"""
        # 清除所有错误样式
        self.clear_card_error_style(self.monitor_path_card)
        self.clear_card_error_style(self.line_name_card)
        self.clear_card_error_style(self.station_card)

        # 调用 cfg 的验证方法
        errors = cfg.validate_settings()

        # 根据验证结果设置错误样式
        if errors.get("monitor_path"):
            self.set_card_error_style(self.monitor_path_card)

        if errors.get("line_name"):
            self.set_card_error_style(self.line_name_card)

        if errors.get("station_code"):
            self.set_card_error_style(self.station_card)

        # 返回是否有错误
        return not any(errors.values())

    def set_card_error_style(self, card):
        """设置卡片错误样式（红色边框）"""
        # 设置属性标记错误状态
        card.setProperty("hasError", True)
        card.style().unpolish(card)
        card.style().polish(card)
        card.update()

    def clear_card_error_style(self, card):
        """清除卡片错误样式"""
        card.setProperty("hasError", False)
        card.style().unpolish(card)
        card.style().polish(card)
        card.update()

    def _create_setting_cards(self):
        """创建所有设置卡片"""

        # 监控路径设置卡
        self.monitor_path_card = PushSettingCard(
            text="选择文件夹",
            icon=FluentIcon.FOLDER,
            title="Log 路径",
            content=cfg.get(cfg.monitor_path),
        )
        self.monitor_path_card.clicked.connect(
            lambda: self._on_select_path(self.monitor_path_card)
        )

        self.csv_path_card = PushSettingCard(
            text="选择文件夹",
            icon=FluentIcon.FOLDER,
            title="CSV 路径",
            content=cfg.get(cfg.csv_path),
        )
        self.csv_path_card.clicked.connect(
            lambda: self._on_select_path(self.csv_path_card)
        )

        self.Raw_data_path_card = PushSettingCard(
            text="选择文件夹",
            icon=FluentIcon.FOLDER,
            title="Raw Data 路径",
            content=cfg.get(cfg.raw_data_path),
        )
        self.Raw_data_path_card.clicked.connect(
            lambda: self._on_select_path(self.Raw_data_path_card)
        )

        # 产线名称设置卡
        self.line_name_card = SettingCard(
            ":app/images/line_icon.svg", "线别", parent=self.scroll_widget
        )
        self.line_name_edit = LineEdit()
        self.line_name_edit.setText(cfg.get(cfg.line_name))
        self.line_name_edit.setPlaceholderText("请输入线别")
        self.line_name_edit.setClearButtonEnabled(True)
        self.line_name_edit.setFixedWidth(250)
        self.line_name_card.hBoxLayout.addWidget(self.line_name_edit)
        self.line_name_card.hBoxLayout.addSpacing(16)

        # 工站名称设置卡

        self.station_card = SettingCard(
            icon=":app/images/station_icon.svg",
            title="工站 Code",
            parent=self.scroll_widget,
        )
        self.station_combo = ComboBox()
        self.station_combo.setFixedWidth(250)

        for code, info in station.items():
            self.station_combo.addItem(f"({code}) {info['name']}", userData=code)

        current_station = cfg.get(cfg.station_code)
        self.station_combo.setCurrentText(
            f"({current_station}) {get_station_config(current_station)['name']}"
        )
        # self.monitor_path_card.setContent(get_station_config(current_station)['log_path'])

        self.station_card.hBoxLayout.addWidget(self.station_combo)
        self.station_card.hBoxLayout.addSpacing(16)

        # 操作员 ID 设置卡
        self.op_id_card = SettingCard(
            FluentIcon.PEOPLE, "OP ID", parent=self.scroll_widget
        )
        self.op_id_edit = LineEdit()
        self.op_id_edit.setText(cfg.get(cfg.op_id))
        self.op_id_edit.setPlaceholderText("请输入操作员 ID")
        self.op_id_edit.setClearButtonEnabled(True)
        self.op_id_edit.setFixedWidth(250)
        self.op_id_card.hBoxLayout.addWidget(self.op_id_edit)
        self.op_id_card.hBoxLayout.addSpacing(16)

        # UOP 模式设置卡
        self.uop_card = SettingCard(
            ":app/images/uop_icon.svg", "UOP 模式", parent=self.scroll_widget
        )
        self.uop_switch = SwitchButton()
        self.uop_switch.setChecked(cfg.get(cfg.uop_mode))
        self.uop_card.hBoxLayout.addWidget(self.uop_switch)
        self.uop_card.hBoxLayout.addSpacing(16)

        self.ftp_card = SettingCard(
            ":app/images/uop_icon.svg", "FTP Server", parent=self.scroll_widget
        )
        self.ftp_switch = SwitchButton()
        self.ftp_switch.setChecked(cfg.get(cfg.ftp_mode))
        self.ftp_card.hBoxLayout.addWidget(self.ftp_switch)
        self.ftp_card.hBoxLayout.addSpacing(16)

        self.raw_card = SettingCard(
            ":app/images/uop_icon.svg", "Raw File Upload", parent=self.scroll_widget
        )
        self.raw_switch = SwitchButton()
        self.raw_switch.setChecked(cfg.get(cfg.raw_upload_mode))
        self.raw_card.hBoxLayout.addWidget(self.raw_switch)
        self.raw_card.hBoxLayout.addSpacing(16)

        self.smb_switch = SettingCard(
            ":app/images/uop_icon.svg", "SMB Upload", parent=self.scroll_widget
        )
        self.smb_switch_button = SwitchButton()
        self.smb_switch_button.setChecked(cfg.get(cfg.enable_smb))
        self.smb_switch.hBoxLayout.addWidget(self.smb_switch_button)
        self.smb_switch.hBoxLayout.addSpacing(16)

        self.Auto_start_switch = SettingCard(
            ":app/images/uop_icon.svg", "开机自启动", parent=self.scroll_widget
        )
        self.Auto_start_switch_button = SwitchButton()
        self.Auto_start_switch_button.setChecked(cfg.get(cfg.Auto_Start))
        self.Auto_start_switch.hBoxLayout.addWidget(self.Auto_start_switch_button)
        self.Auto_start_switch.hBoxLayout.addSpacing(16)

        # IP 地址设置卡
        self.ip_card = SettingCard(
            ":app/images/network_icon.svg", "IP (VIP)", parent=self.scroll_widget
        )
        self.ip_combo = ComboBox()
        ip_options = get_ip_options()
        self.ip_combo.addItems(ip_options)
        current_ip = cfg.get(cfg.ent)
        if current_ip in ip_options:
            self.ip_combo.setCurrentText(current_ip)
        self.ip_combo.setFixedWidth(250)
        self.ip_card.hBoxLayout.addWidget(self.ip_combo)
        self.ip_card.hBoxLayout.addSpacing(16)

        # SFC URL 设置卡（使用展开设置卡）
        self.sfc_url_card = ExpandSettingCard(
            FluentIcon.CLOUD, "SFC Server URL", parent=self.scroll_widget
        )
        self.sfc_url_edit = LineEdit()
        self.sfc_url_edit.setText(cfg.get(cfg.sfc_url))
        self.sfc_url_edit.setClearButtonEnabled(True)
        self.sfc_url_card.viewLayout.addWidget(self.sfc_url_edit)

        # 连接输入框的文本变化信号,实时验证
        self.line_name_edit.textChanged.connect(self._on_line_name_changed)
        self.station_combo.currentIndexChanged.connect(self._on_station_code_changed)

        self.sbm_setting_card = SMBSettingCard(parent=self.scroll_widget)

        self.limits_setting_card = LimitsSettingCard(parent=self.scroll_widget)

        # 添加所有设置卡到布局
        self.setting_layout.addWidget(self.uop_card)

        self.setting_layout.addWidget(self.line_name_card)
        self.setting_layout.addWidget(self.station_card)
        self.setting_layout.addWidget(self.op_id_card)
        self.setting_layout.addWidget(self.ip_card)
        self.setting_layout.addWidget(self.sfc_url_card)
        self.setting_layout.addWidget(self.monitor_path_card)
        self.setting_layout.addWidget(self.limits_setting_card)
        self.setting_layout.addWidget(self.raw_card)
        self.setting_layout.addWidget(self.csv_path_card)
        self.setting_layout.addWidget(self.Raw_data_path_card)
        self.setting_layout.addWidget(self.ftp_card)
        self.setting_layout.addWidget(self.smb_switch)
        self.setting_layout.addWidget(self.Auto_start_switch)
        self.setting_layout.addWidget(self.sbm_setting_card)

        self.setting_layout.addStretch(1)

    def _on_line_name_changed(self, text: str):
        """线别输入框内容变化时的处理"""
        if text.strip():
            self.clear_card_error_style(self.line_name_card)
        else:
            self.set_card_error_style(self.line_name_card)

    def _on_station_code_changed(self, text: str):
        """工站名称输入框内容变化时的处理"""
        station_code = self.station_combo.currentData()
        if station_code:
            station_log_path = get_station_config(station_code)["log_path"]
            self.monitor_path_card.setContent(station_log_path)
            if station_log_path and Path(station_log_path).exists():
                self.clear_card_error_style(self.monitor_path_card)
            else:
                self.set_card_error_style(self.monitor_path_card)

    def _on_select_path(self, event):
        """选择监控路径"""
        if not self.is_unlocked:
            self.show_info_bar("警告", "请先验证密码", InfoBarIcon.WARNING)
            return

        # 获取当前路径作为默认路径
        current_path = event.contentLabel.text()
        current_title = event.titleLabel.text()

        # 打开文件夹选择对话框
        folder_path = QFileDialog.getExistingDirectory(
            self,
            f"选择 {current_title}",
            current_path,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
        )

        # 如果用户选择了路径，更新显示
        if folder_path:
            event.setContent(folder_path)
            self.clear_card_error_style(event)
            self.show_info_bar(
                "成功", f"已选择路径: {folder_path}", InfoBarIcon.SUCCESS
            )

    def save_settings(self):
        """保存设置"""
        # 检查是否已解锁
        if not self.is_unlocked:
            self.show_info_bar("警告", "请先验证密码", InfoBarIcon.WARNING)
            return

        try:
            old_values = {key: cfg.get(key) for key in cfg.RESTART_KEYS}

            # 获取所有设置值
            monitor_path = self.monitor_path_card.contentLabel.text()
            csv_path = self.csv_path_card.contentLabel.text()
            raw_data_path = self.Raw_data_path_card.contentLabel.text()
            line_name = self.line_name_edit.text().strip()
            station_code = self.station_combo.currentData()
            op_id = self.op_id_edit.text().strip()
            uop_mode = self.uop_switch.isChecked()
            ftp_mode = self.ftp_switch.isChecked()
            raw_upload_mode = self.raw_switch.isChecked()
            smb_mode = self.smb_switch_button.isChecked()
            smb_server = self.sbm_setting_card.server_edit.text().strip()
            Auto_start_mode = self.Auto_start_switch_button.isChecked()
            smb_username = self.sbm_setting_card.username_edit.text().strip()
            smb_password = self.sbm_setting_card.password_edit.text().strip()
            smb_share = self.sbm_setting_card.smb_share_edit.text().strip()
            smb_remote_path = self.sbm_setting_card.smb_remote_path_edit.text().strip()
            sfc_url = self.sfc_url_edit.text().strip()
            ent = self.ip_combo.currentText()

            volume_upper = self.limits_setting_card.volume_edit_upper.text().strip()
            volume_lower = self.limits_setting_card.volume_edit_lower.text().strip()
            offset_x_upper = self.limits_setting_card.offset_x_edit_upper.text().strip()
            offset_x_lower = self.limits_setting_card.offset_x_edit_lower.text().strip()
            offset_y_upper = self.limits_setting_card.offset_y_edit_upper.text().strip()
            offset_y_lower = self.limits_setting_card.offset_y_edit_lower.text().strip()

            # 验证必填项
            if not line_name:
                self.show_info_bar("警告", "产线名称不能为空", InfoBarIcon.WARNING)
                return

            # 临时断开 Auto_Start 信号连接，防止保存时触发 _onAutoStartChanged
            cfg.Auto_Start.valueChanged.disconnect(self._onAutoStartChanged)

            try:
                # 保存配置
                cfg.set(cfg.monitor_path, monitor_path)
                cfg.set(cfg.csv_path, csv_path)
                cfg.set(cfg.raw_data_path, raw_data_path)
                cfg.set(cfg.line_name, line_name)
                cfg.set(cfg.station_code, station_code)
                cfg.set(cfg.type, get_station_config(station_code)["type"])
                cfg.set(cfg.face, get_station_config(station_code)["face"])
                cfg.set(cfg.op_id, op_id)
                cfg.set(cfg.uop_mode, uop_mode)
                cfg.set(cfg.ftp_mode, ftp_mode)
                cfg.set(cfg.raw_upload_mode, raw_upload_mode)
                cfg.set(cfg.enable_smb, smb_mode)
                cfg.set(cfg.sfc_url, sfc_url)
                cfg.set(cfg.ent, ent)
                cfg.set(cfg.smb_server, smb_server)
                cfg.set(cfg.Auto_Start, Auto_start_mode)
                cfg.set(cfg.smb_username, smb_username)
                cfg.set(cfg.smb_password, smb_password)
                cfg.set(cfg.smb_share, smb_share)
                cfg.set(cfg.smb_remote_path, smb_remote_path)

                cfg.set(cfg.Volume_upper, volume_upper)
                cfg.set(cfg.Volume_lower, volume_lower)
                cfg.set(cfg.OffsetX_upper, offset_x_upper)
                cfg.set(cfg.OffsetX_lower, offset_x_lower)
                cfg.set(cfg.OffsetY_upper, offset_y_upper)
                cfg.set(cfg.OffsetY_lower, offset_y_lower)
            finally:
                # 重新连接信号
                cfg.Auto_Start.valueChanged.connect(self._onAutoStartChanged)

            # 处理开机自启设置（因为保存时断开了信号，需要手动处理）
            if not DEBUG:
                current_autostart_enabled = self.autoStartManager.is_autostart_enabled()
                if Auto_start_mode and not current_autostart_enabled:
                    # 需要启用但当前未启用
                    self.autoStartManager.enable_autostart()
                elif not Auto_start_mode and current_autostart_enabled:
                    # 需要禁用但当前已启用
                    self.autoStartManager.disable_autostart()

            # 检查是否需要重启
            restart_items = cfg.check_restart_needed(old_values)

            # 保存到文件
            cfg.save()

            self.sbm_setting_card.save()

            # 标记为已保存
            self.settings_saved = True

            # 发送成功信号
            signalBus.infoBarSig.emit("成功", "设置已保存", InfoBarIcon.SUCCESS)
            self.settingsSaved.emit()

            # 如果需要重启，询问用户
            if restart_items:
                # self._ask_restart(restart_items)
                signalBus.appMessageSig.emit("restart")
            # else:
            # 关闭窗口
            self.close()

        except Exception as e:
            self.show_info_bar("错误", f"保存失败: {str(e)}", InfoBarIcon.ERROR)

    def _sync_settings(self):
        """Sync settings from auto start manager"""

        self._syncAutoStartStatus()

    def _syncAutoStartStatus(self):
        """Sync autostart status with system"""
        try:
            is_enabled = self.autoStartManager.is_autostart_enabled()
            cfg.set(cfg.Auto_Start, is_enabled)
        except Exception as e:
            logger.warning(f"Failed to sync autostart status: {e}")

    def _onAutoStartChanged(self, enabled: bool):
        """Handle autostart setting change"""

        # DEBUG模式下不处理开机自启
        if DEBUG:
            return

        # 断开信号以防止递归调用
        cfg.Auto_Start.valueChanged.disconnect(self._onAutoStartChanged)

        try:
            if enabled:
                success = self.autoStartManager.enable_autostart()
                if not success:
                    # 如果设置失败，恢复配置
                    cfg.set(cfg.Auto_Start, False)
                    self.show_info_bar(
                        "", "无法启用开机自启，请检查系统权限", InfoBarIcon.ERROR
                    )
                else:
                    self.show_info_bar("", "已启用开机自启", InfoBarIcon.SUCCESS)
            else:
                success = self.autoStartManager.disable_autostart()
                if not success:
                    # 如果禁用失败，恢复配置
                    cfg.set(cfg.Auto_Start, True)
                    self.show_info_bar(
                        "", "无法禁用开机自启，请检查系统权限", InfoBarIcon.ERROR
                    )
                else:
                    self.show_info_bar("", "已禁用开机自启", InfoBarIcon.SUCCESS)
        except Exception as e:
            # 发生异常时恢复配置
            cfg.set(cfg.Auto_Start, not enabled)
            self.show_info_bar("更改开机自启设置时出错:", str(e), InfoBarIcon.ERROR)
        finally:
            # 重新连接信号
            cfg.Auto_Start.valueChanged.connect(self._onAutoStartChanged)

    def _ask_restart(self, restart_items: list):
        """询问用户是否重启"""
        items_text = "、".join(restart_items)
        msg = MessageBox(
            "需要重启",
            f"修改了以下配置项：{items_text}\n\n这些修改需要重启应用才能生效。\n\n是否立即重启？",
            self,
        )
        msg.yesButton.setText("立即重启")
        msg.cancelButton.setText("稍后重启")

        if msg.exec():
            # 用户选择立即重启
            self.close()
            signalBus.appMessageSig.emit("restart")
        else:
            # 用户选择稍后重启
            self.close()

    def show(self):
        """显示窗口"""
        super().show()
        self.sfc_url_card.setExpand(True)
        self.password_edit.setFocus()

        # 验证配置并显示错误状态
        self.validate_settings()

        # 保存原始值
        # self.original_values = {
        #     'monitor_path': cfg.get(cfg.monitor_path),
        #     'line_name': cfg.get(cfg.line_name),
        #     'station_code': cfg.get(cfg.station_code),
        #     'op_id': cfg.get(cfg.op_id),
        #     'uop_mode': cfg.get(cfg.uop_mode),
        #     'sfc_url': cfg.get(cfg.sfc_url),
        #     'ent': cfg.get(cfg.ent)
        # }
        # self.settings_saved = False

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 如果没有保存,还原monitor_path_card的显示
        # if not self.settings_saved and self.original_values:
        #     original_monitor_path = self.original_values.get('monitor_path', '')
        #     if original_monitor_path:
        #         self.monitor_path_card.setContent(original_monitor_path)

        super().closeEvent(event)

    def show_info_bar(self, title: str, content: str, icon: InfoBarIcon):
        """显示信息栏"""
        _info_bar = InfoBar(
            icon=icon,
            title=title,
            content=content,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self,
        )
        _info_bar.show()


class SMBSettingCard(ExpandGroupSettingCard):
    """SMB 设置卡片"""

    def __init__(self, parent=None):
        super().__init__(icon=FluentIcon.GLOBE, title="SMB 设置", parent=parent)
        # 创建网格布局容器

        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(10)

        # 创建输入框
        self.server_edit = LineEdit()
        self.server_edit.setPlaceholderText("0.0.0.0")
        self.server_edit.setText(cfg.get(cfg.smb_server))

        self.username_edit = LineEdit()
        self.username_edit.setPlaceholderText("admin")
        self.username_edit.setText(cfg.get(cfg.smb_username))
        self.password_edit = LineEdit()
        self.password_edit.setPlaceholderText("foxlink")
        self.password_edit.setText(cfg.get(cfg.smb_password))

        self.smb_share_edit = LineEdit()
        self.smb_share_edit.setPlaceholderText("SharedFolder")
        self.smb_share_edit.setText(cfg.get(cfg.smb_share))

        self.smb_remote_path_edit = LineEdit()
        self.smb_remote_path_edit.setPlaceholderText("CSV")
        self.smb_remote_path_edit.setText(cfg.get(cfg.smb_remote_path))

        # 添加到网格布局 (行, 列, 行跨度, 列跨度)

        grid_layout.addWidget(BodyLabel("服务器地址:"), 0, 0)
        grid_layout.addWidget(self.server_edit, 0, 1)

        grid_layout.addWidget(BodyLabel("用户名:"), 0, 2)
        grid_layout.addWidget(self.username_edit, 0, 3)

        grid_layout.addWidget(BodyLabel("密码:"), 1, 2)
        grid_layout.addWidget(self.password_edit, 1, 3)

        grid_layout.addWidget(BodyLabel("共享名称:"), 1, 0)
        grid_layout.addWidget(self.smb_share_edit, 1, 1)

        grid_layout.addWidget(BodyLabel("远程路径:"), 2, 0)
        grid_layout.addWidget(self.smb_remote_path_edit, 2, 1, 1, 3)
        # 将网格布局添加到卡片
        self.addGroupWidget(grid_widget)

    def save(self):
        """保存 SMB 设置到配置"""
        cfg.set(cfg.smb_server, self.server_edit.text().strip())

        cfg.set(cfg.smb_username, self.username_edit.text().strip())
        cfg.set(cfg.smb_password, self.password_edit.text().strip())
        cfg.set(cfg.smb_share, self.smb_share_edit.text().strip())
        cfg.set(cfg.smb_remote_path, self.smb_remote_path_edit.text().strip())

    def set_enabled(self, enabled: bool):
        """设置是否启用"""
        self.server_edit.setEnabled(enabled)
        self.username_edit.setEnabled(enabled)
        self.password_edit.setEnabled(enabled)
        self.smb_share_edit.setEnabled(enabled)
        self.smb_remote_path_edit.setEnabled(enabled)


class LimitsSettingCard(ExpandGroupSettingCard):
    """Limits 设置卡片"""

    def __init__(self, parent=None):
        super().__init__(icon=FluentIcon.GLOBE, title="Limits 设置", parent=parent)
        # 创建网格布局容器

        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(10)

        # 创建输入框

        self.upper_label = BodyLabel("Upper Limit")
        self.lower_label = BodyLabel("Lower Limit")

        self.volume_edit_upper = LineEdit()
        self.volume_edit_upper.setPlaceholderText("0")
        self.volume_edit_upper.setText(str(cfg.get(cfg.Volume_upper)))

        self.volume_edit_lower = LineEdit()
        self.volume_edit_lower.setPlaceholderText("0")
        self.volume_edit_lower.setText(str(cfg.get(cfg.Volume_lower)))
        self.offset_x_edit_upper = LineEdit()
        self.offset_x_edit_upper.setPlaceholderText("0")
        self.offset_x_edit_upper.setText(str(cfg.get(cfg.OffsetX_upper)))

        self.offset_x_edit_lower = LineEdit()
        self.offset_x_edit_lower.setPlaceholderText("0")
        self.offset_x_edit_lower.setText(str(cfg.get(cfg.OffsetX_lower)))
        self.offset_y_edit_upper = LineEdit()
        self.offset_y_edit_upper.setPlaceholderText("0")
        self.offset_y_edit_upper.setText(str(cfg.get(cfg.OffsetY_upper)))

        self.offset_y_edit_lower = LineEdit()
        self.offset_y_edit_lower.setPlaceholderText("0")
        self.offset_y_edit_lower.setText(str(cfg.get(cfg.OffsetY_lower)))

        # 添加到网格布局 (行, 列, 行跨度, 列跨度)
        upper_label = BodyLabel("Upper Limit")
        upper_label.setAlignment(Qt.AlignCenter)
        lower_label = BodyLabel("Lower Limit")
        lower_label.setAlignment(Qt.AlignCenter)

        grid_layout.addWidget(upper_label, 0, 1)
        grid_layout.addWidget(lower_label, 0, 2)

        grid_layout.addWidget(BodyLabel("Volume: "), 1, 0)
        grid_layout.addWidget(self.volume_edit_upper, 1, 1)
        grid_layout.addWidget(self.volume_edit_lower, 1, 2)

        grid_layout.addWidget(BodyLabel("Offset X: "), 2, 0)
        grid_layout.addWidget(self.offset_x_edit_upper, 2, 1)
        grid_layout.addWidget(self.offset_x_edit_lower, 2, 2)

        grid_layout.addWidget(BodyLabel("Offset Y: "), 3, 0)
        grid_layout.addWidget(self.offset_y_edit_upper, 3, 1)
        grid_layout.addWidget(self.offset_y_edit_lower, 3, 2)

        self.addGroupWidget(grid_widget)

    def save(self):
        """保存 SMB 设置到配置"""
        cfg.set(cfg.smb_server, self.server_edit.text().strip())

        cfg.set(cfg.smb_username, self.username_edit.text().strip())
        cfg.set(cfg.smb_password, self.password_edit.text().strip())
        cfg.set(cfg.smb_share, self.smb_share_edit.text().strip())
        cfg.set(cfg.smb_remote_path, self.smb_remote_path_edit.text().strip())

    def set_enabled(self, enabled: bool):
        """设置是否启用"""
        self.server_edit.setEnabled(enabled)
        self.username_edit.setEnabled(enabled)
        self.password_edit.setEnabled(enabled)
        self.smb_share_edit.setEnabled(enabled)
        self.smb_remote_path_edit.setEnabled(enabled)
