import os
from pathlib import Path
import subprocess
import sys
import time
import shutil
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

os.chdir(Path(__file__).parent)


def clean_build_dirs():
    """清理构建相关的目录"""
    dirs_to_clean = [".pyarmor", "dist", "build", "__pycache__"]

    logger.info("🧹 清理构建目录...")
    for dir_name in dirs_to_clean:
        dir_path = Path(dir_name)
        if dir_path.exists():
            shutil.rmtree(dir_path, ignore_errors=True)
            logger.info(f"  ✓ 已清理: {dir_name}")


def run_with_high_priority(cmd, **kwargs):
    """
    跨平台高优先级运行 subprocess 命令，支持实时输出
    """
    platform = sys.platform

    if platform == "win32":
        kwargs.setdefault("creationflags", 0)
        kwargs["creationflags"] |= subprocess.HIGH_PRIORITY_CLASS

    elif platform == "darwin":
        # root 才能设置到 -20
        nice_val = "-20" if os.geteuid() == 0 else "-10"
        if isinstance(cmd, list):
            cmd = ["nice", "-n", nice_val] + cmd
        else:
            cmd = f"nice -n {nice_val} {cmd}"
        kwargs.setdefault("shell", isinstance(cmd, str))

    cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
    logger.info(f"🚀 运行命令: {cmd_str}")

    # 移除 check=True，由函数自身处理错误退出，避免 CalledProcessError 吞掉实际错误信息
    kwargs.pop("check", None)
    result = subprocess.run(cmd, **kwargs)

    if result.returncode != 0:
        logger.error(f"❌ 命令执行失败，退出码: {result.returncode}")
        if result.stderr:
            logger.error(f"错误输出:\n{result.stderr.decode(errors='replace').strip()}")
        sys.exit(result.returncode)

    return result


def build_with_pyarmor():
    """使用 PyArmor 加密 Python 代码"""
    logger.info("\n" + "=" * 60)
    logger.info("📦 步骤 1/2: 使用 PyArmor 加密代码")
    logger.info("=" * 60)

    script_files = [
        "version.py",
        "resource.py",
        "main.py",
    ]

    pyarmor_command = [
        "pyarmor",
        "gen",
        "-r",
        "--exclude",
        "app/parsers/*.csv",
        "--exclude",
        "app/parsers/*.txt",
        "-O",
        "dist/encrypted_source",
        "app/",
    ]
    pyarmor_command.extend(script_files)

    step_start = time.time()
    run_with_high_priority(pyarmor_command)
    step_time = time.time() - step_start

    logger.info(f"✓ PyArmor 加密完成 (耗时: {step_time:.2f} 秒)")


def build_with_pyinstaller():
    """使用 PyInstaller 打包应用"""
    logger.info("\n" + "=" * 60)
    logger.info("📦 步骤 2/2: 使用 PyInstaller 打包应用")
    logger.info("=" * 60)

    pyinstaller_command = [
        "pyinstaller",
        "-y",
        "--clean",
        "smt-data-collector.spec",
    ]

    step_start = time.time()
    run_with_high_priority(pyinstaller_command)
    step_time = time.time() - step_start

    logger.info(f"✓ PyInstaller 打包完成 (耗时: {step_time:.2f} 秒)")


def verify_build():
    """验证构建结果"""
    logger.info("\n🔍 验证构建结果...")

    dist_dir = Path("dist")
    if not dist_dir.exists():
        logger.error("❌ dist 目录不存在")
        return False

    # 检查是否有构建产物
    items = list(dist_dir.iterdir())
    if not items:
        logger.error("❌ dist 目录为空")
        return False

    logger.info(f"✓ 构建产物: {items[0].name}")
    return True


if __name__ == "__main__":
    try:
        logger.info("\n" + "🏗️  开始构建 smt-data-collector" + "\n")
        start_time = time.time()

        # 清理构建目录
        clean_build_dirs()

        # PyArmor 加密
        build_with_pyarmor()

        # PyInstaller 打包
        build_with_pyinstaller()

        # 验证构建结果
        if not verify_build():
            logger.error("\n❌ 构建验证失败")
            sys.exit(1)

        elapsed_time = time.time() - start_time
        logger.info("\n" + "=" * 60)
        logger.info(f"🎉 构建成功! 总耗时: {elapsed_time:.2f} 秒")
        logger.info("=" * 60 + "\n")

    except KeyboardInterrupt:
        logger.warning("\n⚠️  构建已被用户中断")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n❌ 构建失败: {e}", exc_info=True)
        sys.exit(1)
