from pathlib import Path
import sys
from PySide6.QtCore import QStandardPaths
from version import get_version

DEBUG = not (
    "__compiled__" in globals()  # Nuitka
    or getattr(sys, "frozen", False)  # PyInstaller
)

VERSION = get_version()
APP_NAME = "SMT Data Collector"
SETTINGS_PASSWORD = "123"

if DEBUG:
    APP_PATH = Path("AppData").absolute()
else:
    APP_PATH = (
        Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / APP_NAME
    )

CONFIG_FILE = APP_PATH / "config.json"
DB_PATH = APP_PATH / "database.db"

LOG_PATH = APP_PATH / "logs"
LOG_PATH.mkdir(exist_ok=True, parents=True)

RAW_COUNT_FILE = APP_PATH / "raw_count.json"
# RAW_DATA_FOLDER = Path("D:/AOI Data/Data")
# RAW_DATA_FOLDER.mkdir(exist_ok=True, parents=True)

CSV_PATH = "D:\\ReflowLogs\\CSV"

# FTP 服务器默认配置（凭据由部署环境配置，不写死）
FTP_HOST = "0.0.0.0"
FTP_PORT = 21
FTP_PASSIVE_PORTS = (60000, 60100)
FTP_USER = "admin"
FTP_PASSWORD = ""
MAX_CONNECTIONS = 20
MAX_CONNECTIONS_PER_IP = 5


def GET_VERSION():
    return VERSION
