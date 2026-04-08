from watchdog.events import (
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileSystemEventHandler,
    DirCreatedEvent,
)
from pathlib import Path
import time
from app.common.config import cfg
from app.common.logger import Logger

logger = Logger("Handler")


class EventHandler_AOI_SPI(FileSystemEventHandler):
    def __init__(self, event_queue, state_queue):
        logger.info(
            f"EventHandler_AOI_SPI or Reflow initialized Path: {cfg.get(cfg.monitor_path)}"
        )
        self.event_queue = event_queue
        self.state_queue = state_queue

    def on_created(self, event):
        if not event.is_directory:
            logger.info(f"文件被创建: {event.src_path}")
            self.event_queue.put(event.src_path)

    # def on_modified(self, event):
    #     if not event.is_directory:
    #         logger.info(f"文件被修改: {event.src_path}")
    #         self.event_queue.put(event.src_path)


class EventHandler_Dispensing(FileSystemEventHandler):
    def __init__(self, event_queue, state_queue):
        logger.info(
            f"EventHandler_Dispensing initialized Path: {cfg.get(cfg.monitor_path)}"
        )
        self.event_queue = event_queue
        self.state_queue = state_queue

    def on_created(self, event):
        if isinstance(event, FileCreatedEvent):
            # if Path(event.src_path).parent != Path(cfg.get(cfg.monitor_path)):
            #     return

            if event.src_path.endswith(".txt"):
                logger.info(f"file created: {event.src_path}")
                self.event_queue.put(event.src_path)
