"""工站配置管理模块

提供工站的配置信息，包括类型、名称、UI组件类和日志路径等。
通过配置驱动的方式支持多种工站类型的动态界面。
"""

from typing import Dict, Tuple, Type, Optional
from app.view import aoi_spi_widget, dispensing_widget, reflow_widget

SPI_LOG_PATH = "D:\\OUTPUTPATH"
AOI_LOG_PATH = "D:\\TEST_AOI"
REFLOW_LOG_PATH = "C:\\TestLog"
REFLOW_CSV_PATH = "D:\\ReflowLogs\\CSV"
DISPENSING_LOG_PATH = ""

# 工站配置字典
# 键: 工站代码 (str)
# 值: 包含 code, type, name, ui (StatusTable类, ContentTable类), log_path 等配置
station: Dict[str, dict] = {
    "103": {
        "code": "103",
        "type": "SPI",
        "face": "BOT",
        "name": "SPI (锡膏印刷检测BOT)",
        "ui": (aoi_spi_widget.StatusTable, aoi_spi_widget.ContentTable),
        "log_path": SPI_LOG_PATH,
    },
    "106": {
        "code": "106",
        "type": "SPI",
        "name": "SPI (锡膏印刷检测TOP)",
        "face": "TOP",
        "ui": (aoi_spi_widget.StatusTable, aoi_spi_widget.ContentTable),
        "log_path": SPI_LOG_PATH,
    },
    # "108": {
    #     "code": "108",
    #     "type": "AOI",
    #     "name": "Pre-AOI (AOI贴片检查)",
    #     "ui": (aoi_spi_widget.StatusTable, aoi_spi_widget.ContentTable),
    #     "log_path": AOI_LOG_PATH,
    # },
    "109": {
        "code": "109",
        "type": "Reflow-109",
        "name": "1st HTS Reflow (回流焊)",
        "face": "",
        "ui": (reflow_widget.StatusTable, reflow_widget.ContentTable),
        "log_path": REFLOW_LOG_PATH,
        "csv_path": REFLOW_CSV_PATH,
    },
    # "110": {
    #     "code": "110",
    #     "type": "AOI",
    #     "name": "Post-AOI (AOI炉后检查)",
    #     "ui": (aoi_spi_widget.StatusTable, aoi_spi_widget.ContentTable),
    #     "log_path": AOI_LOG_PATH,
    # },
    "112": {
        "code": "112",
        "type": "SPI",
        "face": "TOP",
        "name": "SPI (锡膏印刷检测TOP)",
        "ui": (aoi_spi_widget.StatusTable, aoi_spi_widget.ContentTable),
        "log_path": SPI_LOG_PATH,
    },
    "116": {
        "code": "116",
        "type": "SPI",
        "face": "TOP",
        "name": "SPI (锡膏印刷检测TOP)",
        "ui": (aoi_spi_widget.StatusTable, aoi_spi_widget.ContentTable),
        "log_path": SPI_LOG_PATH,
    },
    # "113": {
    #     "code": "113",
    #     "type": "Dispensing",
    #     "name": "TOP Signal Pads Dispensing Flux (TOP信號pad點膠)",
    #     "ui": (dispensing_widget.StatusTable, dispensing_widget.ContentTable),
    #     "log_path": DISPENSING_LOG_PATH,
    #     "scan_path": "D:\\SCAN",
    #     "sfc_result_path": "D:\\SFC_RESULT",
    # },
    "122": {
        "code": "122",
        "type": "Reflow-122",
        "face": "",
        "name": "1st HTS Reflow (回流焊)",
        "ui": (reflow_widget.StatusTable, reflow_widget.ContentTable),
        "log_path": REFLOW_LOG_PATH,
        "csv_path": REFLOW_CSV_PATH,
    },
}


def get_station_ui_classes(station_code: str) -> Optional[Tuple[Type, Type]]:
    """获取指定工站的UI组件类

    Args:
        station_code: 工站代码

    Returns:
        包含状态表格类和内容表格类的元组，如果不存在则返回 None
    """
    config = station.get(station_code)
    if config:
        return config.get("ui")
    return None


def get_station_config(station_code: str) -> Optional[dict]:
    """获取指定工站的配置

    Args:
        station_code: 工站代码

    Returns:
        工站配置字典，如果不存在则返回 None
    """
    return station.get(station_code)


def get_available_stations() -> list:
    """获取所有可用的工站代码列表

    Returns:
        工站代码列表
    """
    return list(station.keys())


def validate_station_config(station_code: str) -> bool:
    """验证工站配置是否完整有效

    Args:
        station_code: 工站代码

    Returns:
        配置有效返回 True，否则返回 False
    """
    config = station.get(station_code)
    if not config:
        return False

    required_keys = ["code", "type", "name", "ui", "log_path"]
    for key in required_keys:
        if key not in config:
            return False

    # 验证 ui 配置是否是元组且包含两个类
    ui_config = config.get("ui")
    if not isinstance(ui_config, tuple) or len(ui_config) != 2:
        return False

    return True
