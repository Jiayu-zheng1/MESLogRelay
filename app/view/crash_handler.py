# coding:utf-8
import sys
import os
import traceback
import threading
import platform
import subprocess
import faulthandler
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QTimer, Qt, Slot, QEventLoop
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    PrimaryPushButton,
    PushButton,
    StrongBodyLabel,
    BodyLabel,
    TextEdit,
    InfoBarIcon,
)
from app.common.signal_bus import signalBus


class CrashBridge(QObject):
    """
    Bridge to communicate from non-GUI threads (or signal handlers)
    to the main GUI thread to show the crash dialog.
    """

    crashed = Signal(str, str)  # title, details


class CrashWidget(QWidget):
    """Crash Widget"""

    def __init__(self, title: str, details: str, log_dir: Path, parent=None):
        super().__init__(parent)
        self.log_dir = log_dir
        self.setWindowTitle("Crash Report")
        self.resize(600, 500)

        self.setWindowIcon(InfoBarIcon.ERROR.qicon())
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setWindowModality(Qt.ApplicationModal)

        # Remove default title bar for a cleaner look if desired,
        # but standard dialog frame is safer for crash reporters.
        # self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        # For now, keep standard frame to ensure it's movable/closable easily in panic state.

        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        self.vBoxLayout.setSpacing(15)

        # Header
        self.titleLabel = StrongBodyLabel(
            f"An unexpected error occurred: {title}", self
        )
        self.titleLabel.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #d13438;"
        )  # Error red color
        self.vBoxLayout.addWidget(self.titleLabel)

        self.infoLabel = BodyLabel(
            "The application has encountered a critical error. Details have been saved to Crash.log.",
            self,
        )
        self.infoLabel.setWordWrap(True)
        self.vBoxLayout.addWidget(self.infoLabel)

        # Details Text Area
        self.detailsEdit = TextEdit(self)
        self.detailsEdit.setPlainText(details)
        self.detailsEdit.setReadOnly(True)
        # Use a monospace font
        font = QFont("Consolas", 10)
        if not font.exactMatch():
            font = QFont("Courier New", 10)
        self.detailsEdit.setFont(font)
        self.vBoxLayout.addWidget(self.detailsEdit)

        # Buttons
        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setSpacing(10)
        self.buttonLayout.addStretch(1)

        self.copyBtn = PushButton("Copy Details", self)
        self.copyBtn.clicked.connect(self._copy_details)
        self.buttonLayout.addWidget(self.copyBtn)

        self.openFolderBtn = PushButton("Open Log Folder", self)
        self.openFolderBtn.clicked.connect(self._open_folder)
        self.buttonLayout.addWidget(self.openFolderBtn)

        self.restartBtn = PrimaryPushButton("Restart Application", self)
        self.restartBtn.clicked.connect(self._restart_app)
        self.buttonLayout.addWidget(self.restartBtn)

        self.closeBtn = PushButton("Close", self)
        self.closeBtn.clicked.connect(self.close)
        self.buttonLayout.addWidget(self.closeBtn)

        self.vBoxLayout.addLayout(self.buttonLayout)

    def _copy_details(self):
        QApplication.clipboard().setText(self.detailsEdit.toPlainText())
        self.copyBtn.setText("Copied!")
        QTimer.singleShot(2000, lambda: self.copyBtn.setText("Copy Details"))

    def _open_folder(self):
        folder = str(self.log_dir)
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder])
            else:
                subprocess.run(["xdg-open", folder])
        except Exception:
            pass

    def _restart_app(self):
        try:
            signalBus.appMessageSig.emit("restart")
        except Exception:
            pass


class CrashHandler:
    def __init__(self, log_dir: Path):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.crash_log = self.log_dir / "Crash.log"
        self.bridge = CrashBridge()
        self._crash_widget = None  # Keep reference to prevent GC

        # Connect the signal to the slot that shows the dialog
        # QueuedConnection ensures it runs in the main thread
        self.bridge.crashed.connect(self._show_crash, Qt.QueuedConnection)

    def setup(self):
        """
        Setup global exception hooks and native fault handlers.
        """
        # 1. Native Crash (C/C++ segfaults, etc.)
        try:
            self._crash_file = open(self.crash_log, "a", buffering=1, encoding="utf-8")
            faulthandler.enable(file=self._crash_file, all_threads=True)
        except Exception:
            pass

        # 2. Unhandled Python Exception (Main Thread)
        sys.excepthook = self._sys_excepthook

        # 3. Unhandled Python Exception (Threads - Python 3.8+)
        if hasattr(threading, "excepthook"):
            threading.excepthook = self._threading_excepthook

    def _get_system_info(self):
        """Collect system environment info for debugging."""
        try:
            return (
                f"Time: {datetime.now().isoformat()}\n"
                f"Platform: {platform.platform()}\n"
                f"Python: {sys.version}\n"
                f"System: {platform.system()} {platform.release()} {platform.version()}\n"
                f"Machine: {platform.machine()}\n"
            )
        except Exception:
            return "System info unavailable\n"

    def _write_log(self, title: str, body: str):
        """Write the crash report to the log file."""
        try:
            sys_info = self._get_system_info()
            log_content = (
                f"\n{'=' * 30} CRASH REPORT {'=' * 30}\n"
                f"Type: {title}\n"
                f"{sys_info}"
                f"{'-' * 74}\n"
                f"{body}\n"
                f"{'=' * 74}\n"
            )
            with open(self.crash_log, "a", encoding="utf-8") as f:
                f.write(log_content)
        except Exception:
            traceback.print_exc()

    def _format_exc(self, exc_type, exc, tb):
        return "".join(traceback.format_exception(exc_type, exc, tb))

    def _sys_excepthook(self, exc_type, exc, tb):
        """Handle main thread exceptions."""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return

        details = self._format_exc(exc_type, exc, tb)
        self._write_log("Main Thread Exception", details)

        self.bridge.crashed.emit("Application Exception", details)

    def _threading_excepthook(self, args):
        """Handle thread exceptions."""
        if isinstance(args.exc_type, KeyboardInterrupt):
            return

        details = self._format_exc(args.exc_type, args.exc_value, args.exc_traceback)
        thread_name = args.thread.name if args.thread else "Unknown Thread"
        self._write_log(f"Thread Exception ({thread_name})", details)

        self.bridge.crashed.emit(f"Exception in {thread_name}", details)

    @Slot(str, str)
    def _show_crash(self, title: str, details: str):
        """Show the crash widget."""
        try:
            # We create a new widget instance every time to avoid state issues
            self._crash_widget = CrashWidget(title, details, self.log_dir)

            # Ensure the widget is deleted when closed to trigger destroyed signal
            self._crash_widget.setAttribute(Qt.WA_DeleteOnClose)

            self._crash_widget.show()

            # Block execution using a local event loop
            loop = QEventLoop()
            self._crash_widget.destroyed.connect(loop.quit)
            loop.exec_()

            # Force exit the application after the crash dialog is closed
            # sys.exit(1)

        except Exception:
            print("Failed to show crash widget:")
            traceback.print_exc()
            # Ensure we exit even if UI fails
            sys.exit(1)
