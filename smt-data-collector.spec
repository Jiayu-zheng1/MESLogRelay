# -*- mode: python ; coding: utf-8 -*-

import sys
import toml
import tempfile
import os
import shutil
from pathlib import Path
from PyInstaller.building.api import PYZ, EXE
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.datastruct import logger

sys.path.append(os.path.abspath(os.getcwd()))

import version

# 版本信息
version_str = version.__version__
description = version.__description__
version_tuple = version.get_version_tuple()
logger.info(f"📦 打包版本: {version_str}")

# ---- 创建临时目录并生成 version.txt ----
tmp_dir = tempfile.mkdtemp()
version_file_path = os.path.join(tmp_dir, "version.txt")

version_txt = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple},
    prodvers={version_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        '040904B0',
        [StringStruct('CompanyName', 'Foxlink'),
        StringStruct('FileDescription', '{description}'),
        StringStruct('FileVersion', '{version_str}'),
        StringStruct('InternalName', 'smt-data-collector'),
        StringStruct('LegalCopyright', '(c) 2025 TE Company'),
        StringStruct('OriginalFilename', 'smt-data-collector.exe'),
        StringStruct('ProductName', 'SMT Data Collector'),
        StringStruct('ProductVersion', '{version_str}')])
      ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""

Path(version_file_path).write_text(version_txt, encoding="utf-8")
logger.info(f" version.txt 生成于临时目录：{version_file_path}")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=["hooks"],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pkg_resources", "setuptools"],
    noarchive=False,
    optimize=0,
)


# Pyarmor patch start:
def apply_pyarmor_patch():
    # 动态获取当前工作目录
    current_dir = os.path.abspath(os.getcwd())
    srcpath = [current_dir]
    obfpath = os.path.join(current_dir, "dist", "encrypted_source")
    pkgname = "pyarmor_runtime_000000"
    pkgpath = os.path.join(obfpath, pkgname)

    # 根据操作系统选择正确的扩展名
    ext_name = "pyarmor_runtime.pyd"
    extpath = os.path.join(pkgname, ext_name)

    if hasattr(a.pure, "_code_cache"):
        code_cache = a.pure._code_cache
    else:
        from PyInstaller.config import CONF

        code_cache = CONF["code_cache"].get(id(a.pure))

    srclist = [os.path.normcase(x) for x in srcpath]

    def match_obfuscated_script(orgpath):
        for x in srclist:
            if os.path.normcase(orgpath).startswith(x):
                return os.path.join(obfpath, orgpath[len(x) + 1 :])

    count = 0
    for i in range(len(a.scripts)):
        x = match_obfuscated_script(a.scripts[i][1])
        if x and os.path.exists(x):
            a.scripts[i] = a.scripts[i][0], x, a.scripts[i][2]
            count += 1
    if count == 0:
        raise RuntimeError("No obfuscated script found")

    for i in range(len(a.pure)):
        x = match_obfuscated_script(a.pure[i][1])
        if x and os.path.exists(x):
            code_cache.pop(a.pure[i][0], None)
            a.pure[i] = a.pure[i][0], x, a.pure[i][2]

    a.pure.append((pkgname, os.path.join(pkgpath, "__init__.py"), "PYMODULE"))
    a.binaries.append((extpath, os.path.join(obfpath, extpath), "EXTENSION"))


apply_pyarmor_patch()

# Pyarmor patch end.

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f"smt-data-collector_v{version_str}",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # uac_admin=True,  # 以管理员权限运行
    icon="assets/images/logo.ico",
    version=version_file_path,
)

# ---- 清理临时 version.txt ----
try:
    shutil.rmtree(tmp_dir)
    logger.info(f" 已删除临时目录：{tmp_dir}")
except Exception as e:
    logger.warning(f" 删除临时目录失败：{e}")
