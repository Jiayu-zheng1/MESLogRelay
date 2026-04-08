# coding:utf-8
import sys
import os
import atexit
from typing import List

from PySide6.QtCore import QIODevice, Signal, QStandardPaths
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from app.common.logger import Logger
from app.common.signal_bus import signalBus

import portalocker
import re


def sanitize_key(key: str) -> str:
    """Ensure key is safe for Windows QLocalServer"""
    return re.sub(r'[^\w\-]+', '_', key)


class SingletonApplication(QApplication):

    messageSig = Signal(object)
    logger = Logger("Application")

    def __init__(self, argv: List[str], key: str):
        super().__init__(argv)
        self.key = sanitize_key(key)
        self.timeout = 1000
        self.server = QLocalServer(self)
        self.lock_file = None
        self.isRunning = False

        # ----------------------------------------------------------------------
        # 1. portalocker - cross-platform file lock
        # ----------------------------------------------------------------------
        lock_file_path = os.path.join(
            QStandardPaths.writableLocation(QStandardPaths.TempLocation),
            f"{self.key}.lock"
        )

        try:
            self.lock_file = open(lock_file_path, "w")
            portalocker.lock(self.lock_file, portalocker.LOCK_EX | portalocker.LOCK_NB)
            self.logger.info(f"Application lock acquired: {lock_file_path}")
        except Exception:
            # Another instance is running
            self.isRunning = True
            message = " ".join(argv[1:]) if len(argv) > 1 else "show"
            self._sendMessage(message)
            sys.exit(0)

        # 注册退出清理
        atexit.register(self.cleanup)

        # ----------------------------------------------------------------------
        # 2. QLocalServer for IPC messaging
        # ----------------------------------------------------------------------
        QLocalServer.removeServer(self.key)  # 防止残留
        if not self.server.listen(self.key):
            self.logger.error(f"Failed to listen: {self.server.errorString()}")
        else:
            self.server.newConnection.connect(self.__onNewConnection)

    # ----------------------------------------------------------------------
    # send message
    # ----------------------------------------------------------------------
    def _sendMessage(self, message: str):
        socket = QLocalSocket(self)
        socket.connectToServer(self.key, QIODevice.WriteOnly)

        if not socket.waitForConnected(self.timeout):
            self.logger.warning(f"Could not connect to instance: {socket.errorString()}")
            return False

        socket.write(message.encode("utf-8"))
        socket.waitForBytesWritten(self.timeout)
        socket.disconnectFromServer()
        return True

    # 外部调用接口
    def sendMessage(self, message: str):
        if not self.isRunning:
            return False
        return self._sendMessage(message)

    # ----------------------------------------------------------------------
    # receive
    # ----------------------------------------------------------------------
    def __onNewConnection(self):
        socket = self.server.nextPendingConnection()
        if socket and socket.waitForReadyRead(self.timeout):
            message = socket.readAll().data().decode('utf-8')
            signalBus.appMessageSig.emit(message)
            socket.disconnectFromServer()

    # ----------------------------------------------------------------------
    # clean
    # ----------------------------------------------------------------------
    def cleanup(self):
        if self.lock_file:
            try:
                portalocker.unlock(self.lock_file)
                self.lock_file.close()
            except Exception as e:
                self.logger.error(f"Failed to release lock: {e}")