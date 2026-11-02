"""冒烟测试：验证项目元数据一致性与核心模块可导入性。

这些测试不依赖真实设备数据，仅用于 CI 快速反馈：
- 版本号保持单一数据源（version.py 为准，pyproject 动态读取）
- 核心非 GUI 模块可以正常导入（防止重构破坏导入链）

运行: uv run pytest
"""

from pathlib import Path

import version

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_pyproject_uses_dynamic_version():
    """pyproject.toml 应从 version.py 动态读取版本号，避免两处手动同步。"""
    text = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "dynamic = [\"version\"]" in text
    assert "version = { attr = \"version.__version__\" }" in text


def test_version_format():
    """version.py 的版本号应满足 X.Y.Z 格式。"""
    parts = version.get_version_tuple()
    assert len(parts) == 4
    assert all(isinstance(p, int) and p >= 0 for p in parts)
    assert version.__version__ == ".".join(str(p) for p in parts[:3])


def test_core_modules_importable():
    """核心模块应可在无显示器环境下导入（CI 使用 QT_QPA_PLATFORM=offscreen）。"""
    import app.common.const  # noqa: F401
    import app.common.enums  # noqa: F401
    import app.common.station  # noqa: F401
    import app.parsers.parse_dispensing  # noqa: F401
    import app.parsers.parse_reflow_oven  # noqa: F401
    import app.parsers.parse_spi_csv  # noqa: F401
