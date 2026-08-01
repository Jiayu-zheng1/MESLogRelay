"""
版本管理模块
项目版本信息的单一数据源
注意：修改版本号后，需要同步更新 pyproject.toml
"""

# 版本信息
__version__ = "1.4.4"
__description__ = "SMT Data Collector"
__name__ = "smt-data-collector"


def get_version() -> str:
    """获取版本号字符串"""
    return __version__


def get_version_tuple() -> tuple:
    """
    获取版本号元组 (major, minor, patch, build)
    用于 Windows 可执行文件的版本信息
    """
    parts = __version__.split(".")
    while len(parts) < 4:
        parts.append("0")
    return tuple(int(p) for p in parts[:4])


def get_description() -> str:
    """获取项目描述"""
    return __description__


def get_name() -> str:
    """获取项目名称"""
    return __name__


if __name__ == "__main__":
    print(f"项目名称: {__name__}")
    print(f"版本号: {__version__}")
    print(f"版本元组: {get_version_tuple()}")
    print(f"描述: {__description__}")
