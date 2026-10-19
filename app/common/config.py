# coding:utf-8
import sys

from PySide6.QtCore import QLocale, QStandardPaths
from qfluentwidgets import (
    qconfig,
    QConfig,
    ConfigItem,
    OptionsConfigItem,
    BoolValidator,
    OptionsValidator,
    Theme,
    FolderValidator,
    ConfigSerializer,
    RangeConfigItem,
    RangeValidator,
    MessageBox,
    InfoBarIcon,
)

from app.common.const import CONFIG_FILE
from app.common.utils import get_all_ips
from app.common.signal_bus import signalBus
from app.common.station import station, get_station_config


def isWin11():
    return sys.platform == "win32" and sys.getwindowsversion().build >= 22000


def get_ip_options():
    ips = get_all_ips()
    options = [f"{iface}:{ip}" for iface, ip in ips.items()]
    return options if options else [""]


def set_default_ip():
    options = get_ip_options()
    for opt in options:
        _, ip = opt.split(":", 1)
        if "172.32" in ip:
            return opt
    return options[0]


class Config(QConfig):
    """Config of application"""

    monitor_path = ConfigItem("General", "Log Path", "", restart=True)

    csv_path = ConfigItem("General", "CSV Path", "", restart=True)

    scan_sn_path = ConfigItem("General", "Scan SN Path", "", restart=True)

    raw_data_path = ConfigItem("General", "Raw_Data Path", "", restart=True)

    sfc_result_path = ConfigItem("General", "SFC Result Path", "", restart=True)

    line_name = ConfigItem("General", "Line Name", "")

    Auto_Start = ConfigItem("General", "Auto Start", False)

    Volume_upper = ConfigItem("Limits", "Volume_upper", "", restart=False)
    Volume_lower = ConfigItem("Limits", "Volume_lower", "", restart=False)

    OffsetX_upper = ConfigItem("Limits", "OffsetX_upper", "", restart=False)
    OffsetX_lower = ConfigItem("Limits", "OffsetX_lower", "", restart=False)

    OffsetY_upper = ConfigItem("Limits", "OffsetY_upper", "", restart=False)
    OffsetY_lower = ConfigItem("Limits", "OffsetY_lower", "", restart=False)

    # 默认值为空，实际值由用户在设置页配置（本地 AppData/config.json，不入库）
    smb_server = ConfigItem("SMB", "SMB Server", "")
    smb_username = ConfigItem("SMB", "SMB Username", "")
    smb_password = ConfigItem("SMB", "SMB Password", "")
    smb_share = ConfigItem("SMB", "SMB Share", "")
    smb_remote_path = ConfigItem("SMB", "SMB Remote Path", "MESLogRelay")

    station_code = OptionsConfigItem(
        "General",
        "Station Code",
        list(station.keys())[0],
        OptionsValidator(list(station.keys())),
        restart=True,
    )
    face = OptionsConfigItem(
        "General",
        "face",
        list(station.values())[0].get("face", ""),
        OptionsValidator([config.get("face", "") for config in station.values()]),
        restart=True,
    )
    type = OptionsConfigItem(
        "General",
        "type",
        list(station.values())[0].get("type", ""),
        OptionsValidator([config.get("type", "") for config in station.values()]),
        restart=True,
    )
    op_id = ConfigItem("SFC", "Operator ID", "")

    uop_mode = ConfigItem("SFC", "UOP Mode", True)
    ftp_mode = ConfigItem("SFC", "FTP Mode", True)
    raw_upload_mode = ConfigItem("SFC", "Raw Upload mode", True)
    enable_smb = ConfigItem("SMB", "Enable SMB", True)

    # 默认空，SFC 地址在设置页配置
    sfc_url = ConfigItem("SFC", "SFC URL", "")

    ent = OptionsConfigItem(
        "SFC", "IP", set_default_ip(), OptionsValidator(get_ip_options())
    )

    RESTART_KEYS = [
        monitor_path,
        scan_sn_path,
        sfc_result_path,
        raw_data_path,
        uop_mode,
        ftp_mode,
        raw_upload_mode,
        enable_smb,
        smb_server,
        smb_username,
        smb_password,
        smb_share,
        smb_remote_path,
        Auto_Start,
        Volume_lower,
        Volume_upper,
        OffsetX_lower,
        OffsetX_upper,
        OffsetY_lower,
        OffsetY_upper,
        station_code,
    ]

    def get_ip(self):
        """获取纯 IP 地址（去掉网卡接口名称）"""
        ip_str = self.get(self.ent)
        if ":" in ip_str:
            return ip_str.split(":", 1)[1]
        return ip_str

    def validate_settings(self) -> dict:
        """验证配置设置,返回错误信息字典

        Returns:
            dict: {
                'monitor_path': error_message or None,
                'line_name': error_message or None,
                'station_code': error_message or None
            }
        """
        import os

        errors = {}

        # 验证监控路径
        monitor_path = self.get(self.monitor_path)
        if not monitor_path:
            errors["monitor_path"] = "Monitor path is not configured."
        elif not os.path.exists(monitor_path):
            errors["monitor_path"] = f"Monitor path does not exist: {monitor_path}"
        else:
            errors["monitor_path"] = None

        # 验证线别
        line_name = self.get(self.line_name)
        if not line_name or not line_name.strip():
            errors["line_name"] = "Line name is required."
        else:
            errors["line_name"] = None

        # 验证工站名称
        station_code = self.get(self.station_code)
        if not station_code or not station_code.strip():
            errors["station_code"] = "Station code is required."
        else:
            errors["station_code"] = None

        return errors

    def check_restart_needed(self, old: dict):
        changed_items = []
        for key in self.RESTART_KEYS:
            if old[key] != self.get(key):
                changed_items.append(key)
        return changed_items


cfg = Config()

qconfig.load(str(CONFIG_FILE.absolute()), cfg)
