import os
import sys
import logging
import argparse
import threading
from typing import Tuple, Optional

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

from app.common.const import (
    FTP_PORT,
    FTP_HOST,
    FTP_USER,
    FTP_PASSWORD,
    FTP_PASSIVE_PORTS,
    MAX_CONNECTIONS,
    MAX_CONNECTIONS_PER_IP,
)
from app.common.logger import Logger
import threading
from app.common.config import cfg

logger = Logger("FTPServer")


def setup_pyftpdlib_logging():
    """配置 pyftpdlib 使用自定义日志"""
    # 获取 pyftpdlib 的 logger
    pyftpdlib_logger = logging.getLogger("pyftpdlib")

    # 清除现有的处理器
    pyftpdlib_logger.handlers.clear()

    # 添加自定义处理器
    custom_handler = CustomLogHandler()
    custom_handler.setFormatter(logging.Formatter("%(message)s"))
    pyftpdlib_logger.addHandler(custom_handler)

    # 设置日志级别
    pyftpdlib_logger.setLevel(logging.INFO)

    # 防止日志传播到根 logger
    pyftpdlib_logger.propagate = False


# 自定义日志处理器，将 pyftpdlib 的日志重定向到 Logger
class CustomLogHandler(logging.Handler):
    """将 pyftpdlib 日志重定向到自定义 Logger"""

    def emit(self, record):
        try:
            msg = self.format(record)
            level = record.levelname

            if level == "DEBUG":
                logger.debug(msg)
            elif level == "INFO":
                logger.info(msg)
            elif level == "WARNING":
                logger.warning(msg)
            elif level == "ERROR":
                logger.error(msg)
            elif level == "CRITICAL":
                logger.critical(msg)
        except Exception:
            self.handleError(record)


class FTPServerManager:
    """FTP 服务器管理器"""

    def __init__(
        self,
        directory=cfg.get(cfg.raw_data_path),
        host: str = FTP_HOST,
        port: int = FTP_PORT,
        username: str = FTP_USER,
        password: str = FTP_PASSWORD,
        passive_ports: Tuple[int, int] = FTP_PASSIVE_PORTS,
        max_connections: int = MAX_CONNECTIONS,
        max_connections_per_ip: int = MAX_CONNECTIONS_PER_IP,
    ):
        """
        初始化 FTP 服务器管理器

        Args:
            directory: 共享目录路径
            host: 服务器监听地址
            port: 服务器监听端口
            username: FTP 用户名
            password: FTP 密码
            passive_ports: 被动端口范围 (起始端口, 结束端口)
            max_connections: 最大连接数
            max_connections_per_ip: 每个 IP 的最大连接数
        """
        self.directory = directory
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.passive_ports = passive_ports
        self.max_connections = max_connections
        self.max_connections_per_ip = max_connections_per_ip

        self.server: Optional[FTPServer] = None
        self._is_running = False

        self._ftp_mode = cfg.get(cfg.ftp_mode)

        self.server_thread = threading.Thread(target=self.process_server, daemon=True)

    def _setup_directory(self):
        """确保共享目录存在"""
        os.makedirs(self.directory, exist_ok=True)
        logger.info(f"确保目录存在: {self.directory}")

    def _create_authorizer(self) -> DummyAuthorizer:
        """创建授权器并添加用户"""
        authorizer = DummyAuthorizer()
        authorizer.add_user(
            self.username,
            self.password,
            self.directory,
            perm="elradfmw",  # 完整权限: read, write, append, delete, etc.
        )
        logger.info(f"添加用户: {self.username}")
        return authorizer

    def _create_handler(self, authorizer: DummyAuthorizer) -> type:
        """创建并配置 FTP 处理程序"""
        handler = FTPHandler
        handler.authorizer = authorizer
        handler.passive_ports = range(self.passive_ports[0], self.passive_ports[1] + 1)
        handler.banner = "FTP Server Ready"
        return handler

    def _create_server(self, handler: type) -> FTPServer:
        """创建并配置 FTP 服务器"""
        address = (self.host, self.port)
        server = FTPServer(address, handler)
        server.max_cons = self.max_connections
        server.max_cons_per_ip = self.max_connections_per_ip
        return server

    def start(self):
        """启动 FTP 服务器线程"""
        if self._is_running:
            logger.warning("FTP 服务器已经在运行中")
            return

        # 检查 FTP 模式是否启用
        if not cfg.get(cfg.ftp_mode):
            logger.info("FTP 模式未启用，跳过启动")
            return

        # 检查目录是否已配置
        if not self.directory:
            logger.warning("FTP 服务器共享目录未配置，请在设置中配置后重启")
            return

        self.server_thread.start()
        logger.info("FTP 服务器线程已启动")

    def process_server(self):
        """启动 FTP 服务器"""
        if self._is_running:
            logger.warning("FTP 服务器已经在运行中")
            return

        # 检查目录是否已配置
        if not self.directory:
            logger.error("FTP 服务器共享目录未配置，无法启动")
            self._is_running = False
            return

        try:
            # 配置 pyftpdlib 日志
            setup_pyftpdlib_logging()

            # 设置目录
            self._setup_directory()

            # 创建授权器
            authorizer = self._create_authorizer()

            # 创建处理程序
            handler = self._create_handler(authorizer)

            # 创建服务器
            self.server = self._create_server(handler)

            # 记录启动信息
            logger.info(f"FTP 服务器启动在 {self.host}:{self.port}")
            logger.info(f"共享目录: {self.directory}")
            logger.info(
                f"被动端口范围: {self.passive_ports[0]}-{self.passive_ports[1]}"
            )
            logger.info(
                f"最大连接数: {self.max_connections}, 每 IP 最大连接数: {self.max_connections_per_ip}"
            )

            self._is_running = True

            # 启动服务器（阻塞）
            self.server.serve_forever()

        except Exception as e:
            logger.error(f"服务器错误: {str(e)}")
            self._is_running = False

    def stop(self):
        """停止 FTP 服务器"""
        if self.server and self._is_running:
            logger.info("正在停止 FTP 服务器...")
            self.server.close_all()
            self._is_running = False
            logger.info("FTP 服务器已停止")
        else:
            logger.warning("FTP 服务器未运行")

    @property
    def is_running(self) -> bool:
        """检查服务器是否正在运行"""
        return self._is_running

    def get_status(self) -> dict:
        """获取服务器状态信息"""
        return {
            "running": self._is_running,
            "host": self.host,
            "port": self.port,
            "directory": self.directory,
            "passive_ports": self.passive_ports,
            "max_connections": self.max_connections,
            "max_connections_per_ip": self.max_connections_per_ip,
        }


ftp_server_manager = FTPServerManager()


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="Mac FTP 服务器")
    parser.add_argument(
        "--host", default="192.168.48.253", help="服务器监听地址 (默认: 192.168.48.253)"
    )
    parser.add_argument(
        "--port", type=int, default=21, help="服务器监听端口 (默认: 21)"
    )
    parser.add_argument("--user", default="admin", help="FTP 用户名 (默认: admin)")
    parser.add_argument(
        "--password", default="foxlink", help="FTP 密码 (默认: foxlink)"
    )
    parser.add_argument(
        "--directory",
        default=os.path.expanduser("/vault/AOI Data"),
        help="共享目录 (默认: /vault/AOI Data)",
    )
    parser.add_argument(
        "--passive-ports",
        nargs=2,
        type=int,
        default=[60000, 61000],
        metavar=("START", "END"),
        help="被动端口范围 (默认: 60000-61000)",
    )

    args = parser.parse_args()

    # 使用封装的类
    server_manager = FTPServerManager(
        directory=os.path.expanduser(args.directory),
        host=args.host,
        port=args.port,
        username=args.user,
        password=args.password,
        passive_ports=tuple(args.passive_ports),
    )

    try:
        server_manager.start()
    except KeyboardInterrupt:
        server_manager.stop()


if __name__ == "__main__":
    main()
