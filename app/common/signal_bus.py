# coding: utf-8
from PySide6.QtCore import QObject, Signal
from qfluentwidgets import InfoBarIcon
from app.common.enums import UploadStatus


class SignalBus(QObject):
    """Signal bus"""

    appMessageSig = Signal(str)
    appErrorSig = Signal(
        str, str, InfoBarIcon, int
    )  # title, message, icon, duration(ms)

    infoBarSig = Signal(str, str, InfoBarIcon)

    moduleUpdateSignal = Signal(str, bool)

    update_chip_status_signal = Signal(str, bool)  # ChipType, text

    sfc_connect_signal = Signal(bool)

    addStatusRowSig = Signal(object)
    uploadStatusSig = Signal(object, UploadStatus, str)  # object, status, message
    clearStatusTableSig = Signal()

    sfc_status_signal = Signal(object)  # ChipType


signalBus = SignalBus()
