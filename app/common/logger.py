# coding:utf-8
import sys
import weakref
import queue
import threading
import time
import shutil
from pathlib import Path
from typing import Tuple

from loguru import logger
from app.common.const import LOG_PATH

_loggers = weakref.WeakValueDictionary()

# ==================== 轮转后处理：后台搬运 + 清理 ====================

_rotate_q: "queue.Queue[Tuple[Path, Path, int]]" = queue.Queue()
_worker_started = False
_worker_lock = threading.Lock()


def _start_rotate_worker_once():
    global _worker_started
    if _worker_started:
        return
    with _worker_lock:
        if _worker_started:
            return

        def worker():
            while True:
                src_path, archive_dir, keep_days = _rotate_q.get()
                try:
                    # 1) move（加一点重试，兼容 Windows 偶发占用）
                    sub_archive_dir = archive_dir.joinpath(
                        str(src_path.name).split(".")[0]
                    )
                    sub_archive_dir.mkdir(parents=True, exist_ok=True)
                    dst_path = sub_archive_dir / src_path.name

                    for i in range(10):
                        try:
                            # 跨盘符用 shutil.move，同行可用 replace 更快
                            shutil.move(str(src_path), str(dst_path))
                            break
                        except Exception:
                            time.sleep(0.2)
                    # 2) 清理超过 keep_days 的文件（按 mtime）
                    cutoff = time.time() - keep_days * 86400
                    for p in archive_dir.rglob("*.log"):
                        try:
                            if p.is_file() and p.stat().st_mtime < cutoff:
                                p.unlink(missing_ok=True)
                        except Exception:
                            pass
                finally:
                    _rotate_q.task_done()

        threading.Thread(target=worker, daemon=True).start()
        _worker_started = True


def _enqueue_move_and_cleanup(
    rotated_path: str, archive_dir: Path, keep_days: int = 30
):
    try:
        p = Path(rotated_path)
        if p.exists():
            _rotate_q.put((p, archive_dir, keep_days))
    except Exception:
        pass


# ===================================================================


def loggerCache(cls):
    def wrapper(name, *args, **kwargs):
        if name not in _loggers:
            instance = cls(name, *args, **kwargs)
            _loggers[name] = instance
        return _loggers[name]

    return wrapper


_initialized = False


@loggerCache
class Logger:
    """Logger class using loguru"""

    def __init__(self, fileName: str):
        global _initialized

        if hasattr(self, "_init_done"):
            return

        _start_rotate_worker_once()

        # ========= 目录结构 =========
        ARCHIVE_DIR = LOG_PATH / "archive"
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

        self.fileName = fileName
        self.current_log = LOG_PATH / f"{fileName}.log"
        self.handlers = []

        # ========= 只移除一次默认 handler =========
        if not _initialized:
            logger.remove()
            _initialized = True

        # ========= 控制台 =========
        if sys.stdout is not None:
            console_id = logger.add(
                sys.stdout,
                format=(
                    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                    "<level>{level: <8}</level> | "
                    "<cyan>{extra[logger_name]}</cyan> | "
                    "<bold>{message}</bold>"
                ),
                level="INFO",
                colorize=True,
                filter=lambda r: r["extra"].get("logger_name") == fileName,
            )
            self.handlers.append(console_id)

        # ========= 当前日志（每天轮转；轮转后把旧文件搬到 archive；并清理 archive 超过30天）=========
        def _rotate_hook(path: str):
            _enqueue_move_and_cleanup(path, ARCHIVE_DIR, keep_days=30)

        current_id = logger.add(
            self.current_log,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} - {level} - {message}",
            level="DEBUG",
            rotation="00:00",  # 每天一个
            compression=_rotate_hook,  # 用 compression=callable 当“轮转后钩子”
            encoding="utf-8",
            enqueue=True,
            filter=lambda r: r["extra"].get("logger_name") == fileName,
        )
        self.handlers.append(current_id)

        self._init_done = True

    # ========= API 不变 =========
    def info(self, msg):
        logger.bind(logger_name=self.fileName).info(str(msg))

    def error(self, msg, exc_info=False):
        if exc_info:
            logger.bind(logger_name=self.fileName).exception(str(msg))
        else:
            logger.bind(logger_name=self.fileName).error(str(msg))

    def debug(self, msg):
        logger.bind(logger_name=self.fileName).debug(str(msg))

    def warning(self, msg):
        logger.bind(logger_name=self.fileName).warning(str(msg))

    def critical(self, msg):
        logger.bind(logger_name=self.fileName).critical(str(msg))

    def exception(self, msg):
        logger.bind(logger_name=self.fileName).exception(str(msg))
