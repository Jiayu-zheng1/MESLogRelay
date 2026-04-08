"""SMB 挂载管理器 - 更高性能的文件写入方案"""

import sys
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from qfluentwidgets import InfoBarIcon

from app.common.logger import Logger
from app.common.config import cfg
from app.common.signal_bus import signalBus

logger = Logger("SMBMount")


class SMBMountService:
    """SMB 挂载服务单例"""

    _instance = None
    _manager: Optional["SMBMountManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def start(self):
        """启动 SMB 挂载服务 - 在后台线程执行以避免阻塞 UI"""

        # 检查是否启用 SMB
        if not cfg.get(cfg.enable_smb):
            logger.info("SMB is disabled, skipping mount")
            return False

        # 在后台线程中执行挂载操作
        mount_thread = threading.Thread(
            target=self._do_mount, daemon=True, name="SMBMountThread"
        )
        mount_thread.start()
        logger.info("SMB mount service starting in background...")
        return True

    def _do_mount(self):
        """在后台线程中执行实际的挂载操作"""
        try:
            # 创建挂载管理器
            self._manager = SMBMountManager(
                server=cfg.get(cfg.smb_server),
                username=cfg.get(cfg.smb_username),
                password=cfg.get(cfg.smb_password),
                share=cfg.get(cfg.smb_share),
            )

            # 执行挂载
            if self._manager.mount():
                logger.info(
                    f"SMB mount service started successfully at {self._manager.mount_point}"
                )
                return True
            else:
                logger.error("Failed to mount SMB share")
                self._manager = None
                return False

        except Exception as e:
            logger.error(f"Failed to start SMB mount service: {e}", exc_info=True)
            self._manager = None
            return False

    def stop(self):
        """停止 SMB 挂载服务"""
        if self._manager:
            try:
                self._manager.unmount()
                logger.info("SMB mount service stopped")
            except Exception as e:
                logger.error(f"Error stopping SMB mount service: {e}")
            finally:
                self._manager = None

    def get_manager(self) -> Optional["SMBMountManager"]:
        """获取当前挂载管理器"""
        return self._manager

    @property
    def is_mounted(self) -> bool:
        """检查是否已挂载"""
        return self._manager is not None and self._manager.is_mounted


# 全局单例实例
smb_mount_service = SMBMountService()


class SMBMountManager:
    """
    SMB 挂载管理器

    提供自动挂载/卸载功能，使用系统级文件 I/O 代替网络协议，性能更好。
    """

    def __init__(
        self,
        server: str,
        username: str,
        password: str,
        share: str,
        mount_point: Optional[Path] = None,
    ):
        """
        初始化 SMB 挂载管理器

        Args:
            server: SMB 服务器地址
            username: 用户名
            password: 密码
            share: 共享名
            mount_point: 挂载点路径，None 时自动创建临时目录
        """
        self.server = server
        self.username = username
        self.password = password
        self.share = share
        self._is_mounted = False
        self._auto_created_mount = False
        self._unc_path = None  # Windows UNC 路径

        # 确定挂载点
        if mount_point:
            self.mount_point = Path(mount_point)
        else:
            # 创建临时挂载点
            self.mount_point = Path(tempfile.mkdtemp(prefix="smb_mount_"))
            self._auto_created_mount = True

        self.mount_point.mkdir(parents=True, exist_ok=True)

    @property
    def is_mounted(self) -> bool:
        """检查是否已挂载"""
        return self._is_mounted

    def mount(self) -> bool:
        """
        挂载 SMB 共享

        Returns:
            bool: 挂载是否成功
        """
        if self._is_mounted:
            # logger.warning("SMB share is already mounted")
            return True

        try:
            if sys.platform == "darwin":  # macOS
                return self._mount_macos()
            elif sys.platform == "win32":  # Windows
                return self._mount_windows()
            else:
                logger.error(f"Unsupported platform: {sys.platform}")
                return False
        except Exception as e:
            logger.error(f"Failed to mount SMB share: {e}", exc_info=True)
            return False

    def _mount_macos(self) -> bool:
        """macOS 挂载"""
        smb_url = f"smb://{self.username}:{self.password}@{self.server}/{self.share}"

        # 使用 mount_smbfs 命令
        cmd = ["mount", "-t", "smbfs", smb_url, str(self.mount_point)]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                self._is_mounted = True
                logger.info(f"Successfully mounted SMB share to {self.mount_point}")
                return True
            else:
                logger.error(f"Mount failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Mount command timed out")
            signalBus.appErrorSig.emit(
                "错误", "挂载SMB共享超时", InfoBarIcon.ERROR, 3000
            )
            return False
        except Exception as e:
            signalBus.appErrorSig.emit(
                "错误", f"挂载SMB共享失败: {e}", InfoBarIcon.ERROR, 3000
            )
            logger.error(f"Mount command failed: {e}")
            return False

    def _mount_windows(self) -> bool:
        """Windows 挂载"""
        # Windows 使用 net use 命令
        unc_path = f"\\\\{self.server}\\{self.share}"

        # CREATE_NO_WINDOW 标志用于隐藏终端窗口
        CREATE_NO_WINDOW = 0x08000000

        # 先尝试删除已有连接
        subprocess.run(
            ["net", "use", unc_path, "/delete"],
            capture_output=True,
            creationflags=CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

        cmd = [
            "net",
            "use",
            unc_path,
            f"/user:{self.username}",
            self.password,
            "/persistent:no",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=CREATE_NO_WINDOW,
            )

            if result.returncode == 0:
                self._is_mounted = True
                # Windows 直接使用 UNC 路径，保存到 _unc_path 而不是覆盖 mount_point
                self._unc_path = unc_path
                logger.info(f"Successfully connected to SMB share: {unc_path}")
                return True
            else:
                signalBus.appErrorSig.emit(
                    "错误", f"挂载SMB共享失败: {result.stderr}", InfoBarIcon.ERROR, 3000
                )
                logger.error(f"Mount failed: {result.stderr}")
                return False

        except Exception as e:
            signalBus.appErrorSig.emit(
                "错误", f"挂载SMB共享失败: {e}", InfoBarIcon.ERROR, 3000
            )
            logger.error(f"Mount command failed: {e}")
            return False

    def unmount(self) -> bool:
        """
        卸载 SMB 共享

        Returns:
            bool: 卸载是否成功
        """
        if not self._is_mounted:
            return True

        try:
            if sys.platform == "darwin":  # macOS
                success = self._unmount_macos()
            elif sys.platform == "win32":  # Windows
                success = self._unmount_windows()
            else:
                logger.error(f"Unsupported platform: {sys.platform}")
                success = False

            if success:
                self._is_mounted = False

                # 清理自动创建的挂载点
                if self._auto_created_mount:
                    try:
                        self.mount_point.rmdir()
                    except Exception as e:
                        logger.warning(f"Failed to remove mount point: {e}")

            return success

        except Exception as e:
            signalBus.appErrorSig.emit(
                "错误", "卸载SMB共享失败", InfoBarIcon.ERROR, 3000
            )
            logger.error(f"Failed to unmount SMB share: {e}", exc_info=True)
            return False

    def _unmount_macos(self) -> bool:
        """macOS 卸载"""
        cmd = ["umount", str(self.mount_point)]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                logger.info(f"Successfully unmounted {self.mount_point}")
                return True
            else:
                logger.error(f"Unmount failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Unmount command failed: {e}")
            signalBus.appErrorSig.emit(
                "错误", f"卸载SMB共享失败: {e}", InfoBarIcon.ERROR, 3000
            )
            return False

    def _unmount_windows(self) -> bool:
        """Windows self._unc_path or 卸载"""
        unc_path = f"\\\\{self.server}\\{self.share}"
        cmd = ["net", "use", unc_path, "/delete"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                logger.info(f"Successfully disconnected from {unc_path}")
                return True
            else:
                # Windows 可能已经断开，不算错误
                logger.info(f"Disconnect result: {result.stderr}")
                return True

        except Exception as e:
            signalBus.appErrorSig.emit(
                "错误", f"卸载SMB共享失败: {e}", InfoBarIcon.ERROR, 3000
            )
            logger.error(f"Disconnect command failed: {e}")
            return False

    def get_local_path(self, remote_path: str) -> Path:
        """
        将远程路径转换为本地挂载路径

        Args:
            remote_path: 远程相对路径，如 "CSV/file.csv"

        Returns:
            Path: 本地文件系统路径
        """
        # 清理路径分隔符
        clean_path = remote_path.strip("\\/").replace("\\", "/")

        # Windows 使用 UNC 路径
        if sys.platform == "win32" and self._unc_path:
            return Path(self._unc_path) / clean_path

        # macOS/Linux 使用挂载点
        return self.mount_point / clean_path

    @contextmanager
    def mounted(self):
        """
        上下文管理器，自动挂载和卸载

        使用示例:
            with manager.mounted():
                path = manager.get_local_path("CSV/file.csv")
                with open(path, 'w') as f:
                    f.write("data")
        """
        try:
            if self.mount():
                yield self
            else:
                raise RuntimeError("Failed to mount SMB share")
        finally:
            self.unmount()

    def __enter__(self):
        """支持 with 语句"""
        if not self.mount():
            raise RuntimeError("Failed to mount SMB share")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持 with 语句"""
        self.unmount()
        return False

    def __del__(self):
        """析构时自动卸载"""
        if self._is_mounted:
            self.unmount()


if __name__ == "__main__":
    # 测试代码：示例参数，按实际环境填写
    manager = SMBMountManager(
        server="<服务器IP>",
        username="<账号>",
        password="<密码>",
        share="/Volumes/<共享名>/<子目录>",
    )

    # 方式1: 手动挂载/卸载
    print("方式1: 手动挂载")
    if manager.mount():
        print(f"挂载点: {manager.mount_point}")

        # 写入测试文件
        test_file = manager.get_local_path("CSV/test_mount.csv")
        test_file.parent.mkdir(parents=True, exist_ok=True)

        with open(test_file, "w", encoding="utf-8") as f:
            f.write("时间,数据1,数据2\n")
            f.write("2025-12-09 10:00:00,100,200\n")

        print(f"✓ 文件已写入: {test_file}")
        manager.unmount()

    # 方式2: 使用上下文管理器
    print("\n方式2: 上下文管理器")
    with manager.mounted():
        test_file = manager.get_local_path("CSV/test_context.csv")
        test_file.parent.mkdir(parents=True, exist_ok=True)

        with open(test_file, "w", encoding="utf-8") as f:
            f.write("时间,数据1,数据2\n")
            f.write("2025-12-09 10:00:01,101,201\n")

        print(f"✓ 文件已写入: {test_file}")

    print("\n✓ 测试完成")
