# coding:utf-8
import os
import platform
import subprocess
import sys
from pathlib import Path

# 只在 Windows 系统上导入 winreg
if platform.system() == "Windows":
    import winreg

from app.common.logger import Logger
from app.common.const import DEBUG


class AutoStartManager:
    """开机自启动管理器，支持Windows和macOS"""

    def __init__(self):
        self.logger = Logger("AutoStart")
        self.app_name = "Fluent FTP"
        self.logger.info(f"初始化开机自启管理器 - 当前系统: {platform.system()}")
        self.executable_path = self._get_executable_path()
        self.logger.info(f"可执行文件路径: {self.executable_path}")

    def _get_executable_path(self) -> str:
        """获取当前可执行文件路径"""
        if getattr(sys, "frozen", False):
            # 打包后的可执行文件
            self.logger.info("运行环境: 打包后的可执行文件")
            return sys.executable
        else:
            # 开发环境下的Python脚本
            self.logger.info("运行环境: 开发环境Python脚本")
            return sys.executable + " " + os.path.abspath(sys.argv[0])

    def is_autostart_enabled(self) -> bool:
        """检查是否已启用开机自启"""
        self.logger.info("开始检查开机自启状态...")
        if DEBUG:
            self.logger.info("DEBUG模式下禁用开机自启功能")
            return False

        try:
            result = False
            if platform.system() == "Windows":
                self.logger.info("检查Windows开机自启状态")
                result = self._is_windows_autostart_enabled()
            elif platform.system() == "Darwin":
                self.logger.info("检查macOS开机自启状态")
                result = self._is_macos_autostart_enabled()
            else:
                self.logger.warning(f"不支持的操作系统: {platform.system()}")
                return False

            self.logger.info(
                f"开机自启状态检查结果: {'已启用' if result else '未启用'}"
            )
            return result
        except Exception as e:
            self.logger.error(f"检查开机自启状态失败: {e}")
            return False

    def enable_autostart(self) -> bool:
        """启用开机自启"""
        self.logger.info("开始启用开机自启...")
        if DEBUG:
            self.logger.warning("DEBUG模式下无法启用开机自启")
            return False

        try:
            result = False
            if platform.system() == "Windows":
                self.logger.info("使用Windows注册表方式启用开机自启")
                result = self._enable_windows_autostart()
            elif platform.system() == "Darwin":
                self.logger.info("使用macOS LaunchAgent方式启用开机自启")
                result = self._enable_macos_autostart()
            else:
                self.logger.warning(f"不支持的操作系统: {platform.system()}")
                return False

            if result:
                self.logger.info("开机自启启用成功")
            else:
                self.logger.warning("开机自启启用失败")
            return result
        except Exception as e:
            self.logger.error(f"启用开机自启失败: {e}")
            return False

    def disable_autostart(self) -> bool:
        """禁用开机自启"""
        self.logger.info("开始禁用开机自启...")
        if DEBUG:
            self.logger.info("DEBUG模式下禁用开机自启（无操作）")
            return True

        try:
            result = False
            if platform.system() == "Windows":
                self.logger.info("从Windows注册表中移除开机自启项")
                result = self._disable_windows_autostart()
            elif platform.system() == "Darwin":
                self.logger.info("移除macOS LaunchAgent配置")
                result = self._disable_macos_autostart()
            else:
                self.logger.warning(f"不支持的操作系统: {platform.system()}")
                return False

            if result:
                self.logger.info("开机自启禁用成功")
            else:
                self.logger.warning("开机自启禁用失败")
            return result
        except Exception as e:
            self.logger.error(f"禁用开机自启失败: {e}")
            return False

    # Windows 实现
    def _is_windows_autostart_enabled(self) -> bool:
        """检查Windows注册表中是否已设置开机自启"""
        if platform.system() != "Windows":
            self.logger.error("当前系统不是Windows，无法操作Windows注册表")
            return False

        try:
            self.logger.info("正在打开Windows注册表...")
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ,
            )
            try:
                value, _ = winreg.QueryValueEx(key, self.app_name)
                winreg.CloseKey(key)
                self.logger.info(f"找到开机自启项: {self.app_name} = {value}")
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                self.logger.info(f"注册表中未找到开机自启项: {self.app_name}")
                return False
        except Exception as e:
            self.logger.error(f"检查Windows注册表失败: {e}")
            return False

    def _enable_windows_autostart(self) -> bool:
        """在Windows注册表中添加开机自启项"""
        if platform.system() != "Windows":
            self.logger.error("当前系统不是Windows，无法操作Windows注册表")
            return False

        try:
            self.logger.info("正在打开Windows注册表进行写入...")
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            )
            # 添加 --silent 参数用于静默启动
            startup_command = f'"{self.executable_path}" --silent'
            self.logger.info(f"准备写入注册表项: {self.app_name} = {startup_command}")
            winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, startup_command)
            winreg.CloseKey(key)
            self.logger.info("Windows开机自启已启用")
            return True
        except Exception as e:
            self.logger.error(f"启用Windows开机自启失败: {e}")
            return False

    def _disable_windows_autostart(self) -> bool:
        """从Windows注册表中删除开机自启项"""
        if platform.system() != "Windows":
            self.logger.error("当前系统不是Windows，无法操作Windows注册表")
            return False

        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            )
            try:
                winreg.DeleteValue(key, self.app_name)
                winreg.CloseKey(key)
                self.logger.info("Windows开机自启已禁用")
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                self.logger.info("Windows开机自启项不存在")
                return True
        except Exception as e:
            self.logger.error(f"禁用Windows开机自启失败: {e}")
            return False

    # macOS 实现
    def _get_macos_plist_path(self) -> Path:
        """获取macOS LaunchAgent plist文件路径"""
        home = Path.home()
        launch_agents_dir = home / "Library" / "LaunchAgents"
        self.logger.info(f"LaunchAgents目录: {launch_agents_dir}")
        launch_agents_dir.mkdir(exist_ok=True)
        plist_path = launch_agents_dir / "com.fluentftp.autostart.plist"
        self.logger.info(f"Plist文件路径: {plist_path}")
        return plist_path

    def _is_macos_autostart_enabled(self) -> bool:
        """检查macOS LaunchAgent是否已设置"""
        plist_path = self._get_macos_plist_path()
        exists = plist_path.exists()
        self.logger.info(f"Plist文件存在状态: {exists}")
        return exists

    def _enable_macos_autostart(self) -> bool:
        """创建macOS LaunchAgent plist文件"""
        try:
            plist_path = self._get_macos_plist_path()
            self.logger.info(f"准备创建plist文件: {plist_path}")

            # 构建plist内容
            if getattr(sys, "frozen", False):
                # 打包后的应用
                program_arguments = [self.executable_path, "--silent"]
                self.logger.info("使用打包应用路径")
            else:
                # 开发环境
                program_arguments = [
                    sys.executable,
                    os.path.abspath(sys.argv[0]),
                    "--silent",
                ]
                self.logger.info("使用开发环境Python路径")

            self.logger.info(f"程序参数: {program_arguments}")

            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.fluentftp.autostart</string>
    <key>ProgramArguments</key>
    <array>
        {"".join(f"<string>{arg}</string>" for arg in program_arguments)}
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>LaunchOnlyOnce</key>
    <true/>
</dict>
</plist>"""

            # 写入plist文件
            self.logger.info("正在写入plist文件...")
            with open(plist_path, "w", encoding="utf-8") as f:
                f.write(plist_content)
            self.logger.info("Plist文件写入成功")

            # 加载LaunchAgent
            self.logger.info("正在加载LaunchAgent...")
            subprocess.run(["launchctl", "load", str(plist_path)], check=True)
            self.logger.info("macOS开机自启已启用")
            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"加载LaunchAgent失败: {e}")
            return False
        except Exception as e:
            self.logger.error(f"创建macOS开机自启失败: {e}")
            return False

    def _disable_macos_autostart(self) -> bool:
        """删除macOS LaunchAgent plist文件"""
        try:
            plist_path = self._get_macos_plist_path()

            if plist_path.exists():
                self.logger.info(f"找到plist文件: {plist_path}")
                # 卸载LaunchAgent
                try:
                    self.logger.info("正在卸载LaunchAgent...")
                    subprocess.run(["launchctl", "unload", str(plist_path)], check=True)
                    self.logger.info("LaunchAgent卸载成功")
                except subprocess.CalledProcessError as e:
                    # 如果unload失败，可能是因为已经卸载了，继续删除文件
                    self.logger.warning(f"LaunchAgent卸载失败（可能已卸载）: {e}")
                    pass

                # 删除plist文件
                self.logger.info("正在删除plist文件...")
                plist_path.unlink()
                self.logger.info("macOS开机自启已禁用")
            else:
                self.logger.info("macOS开机自启项不存在")

            return True

        except Exception as e:
            self.logger.error(f"禁用macOS开机自启失败: {e}")
            return False
