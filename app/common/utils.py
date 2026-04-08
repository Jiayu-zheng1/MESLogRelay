import ctypes
import os
from pathlib import Path
from sys import platform
import socket
from typing import Union
from pprint import pformat

import psutil
from PySide6.QtCore import QProcess

from app.common.logger import Logger
logger = Logger('Utils')

def get_all_ips():
    ips = {}
    addrs = psutil.net_if_addrs()
    for iface, addr_list in addrs.items():
        for addr in addr_list:
            if addr.family == socket.AF_INET:
                ips[iface] = addr.address
    logger.debug(f"Detected IP addresses: {pformat(ips)}")
    return ips

def runProcess(executable: Union[str, Path], args=None, timeout=5000, cwd=None) -> str:
    process = QProcess()

    if cwd:
        process.setWorkingDirectory(str(cwd))

    process.start(str(executable).replace("\\", "/"), args or [])
    process.waitForFinished(timeout)
    return process.readAllStandardOutput().toStdString()


def runDetachedProcess(executable: Union[str, Path], args=None, cwd=None):
    process = QProcess()

    if cwd:
        process.setWorkingDirectory(str(cwd))

    process.startDetached(str(executable).replace("\\", "/"), args or [])

def is_admin():
    """判断当前进程是否是管理员权限"""
    system = platform.system()
    if system in ("Darwin", "Linux"):
        return os.geteuid() == 0
    elif system == "Windows":
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    return False
