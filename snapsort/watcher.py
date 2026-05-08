
import logging
import time
from pathlib import Path
from typing import FrozenSet, Optional

from watchdog.events import FileCreatedEvent, FileMovedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .indexer import generate_index
from .metadata import extract_metadata
from .renamer import is_canonical, rename_file

logger = logging.getLogger(__name__)

_DEFAULT_EXTENSIONS: FrozenSet[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".tif"}
)
_SETTLE_SECONDS = 1.5
_SETTLE_TIMEOUT = 15.0


class ScreenshotHandler(FileSystemEventHandler):
    def __init__(self, config: dict) -> None:
        super().__init__()
        self.watch_folder = Path(config["watch_folder"]).expanduser().resolve()

        out = config.get("output_folder") or ""
        self.output_folder = (
            Path(out).expanduser().resolve() if out else self.watch_folder
        )

        self.backup_dir: Optional[Path] = None
        if config.get("backup"):
            bp = config.get("backup_folder", ".backup")
            self.backup_dir = (
                Path(bp).expanduser().resolve()
                if Path(bp).is_absolute()
                else self.watch_folder / bp
            )

        self.extensions: FrozenSet[str] = frozenset(
            ext.lower()
            for ext in config.get("image_extensions", list(_DEFAULT_EXTENSIONS))
        )
        self.thumb_size: tuple = tuple(config.get("thumb_size", [200, 150]))
        self.index_filename: str = config.get("index_filename", "index.html")
        self.date_subfolders: bool = bool(config.get("date_subfolders", False))

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.name.startswith('.'):
            return
        if path.suffix.lower() not in self.extensions:
            return
        if is_canonical(path.name) and path.parent.resolve() == self.output_folder:
            return
        self._process(path)

    def on_moved(self, event: FileMovedEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.dest_path)
        if path.name.startswith('.'):
            return
        if path.suffix.lower() not in self.extensions:
            return
        if is_canonical(path.name) and path.parent.resolve() == self.output_folder:
            return
        self._process(path)

    def _process(self, src: Path) -> None:
        self._wait_for_stable(src)
        if not src.exists():
            return

        try:
            meta = extract_metadata(src)
            dest_dir = self.output_folder
            if self.date_subfolders:
                dest_dir = dest_dir / meta["date"].strftime("%Y/%m-%d")

            new_path = rename_file(src, dest_dir, meta["date"], meta["app"], self.backup_dir)
            if new_path != src:
                logger.info("Renamed  %s  ->  %s", src.name, new_path.name)
            else:
                logger.info("Skipped (already canonical): %s", src.name)

            self._rebuild_index()
        except Exception as exc:
            logger.error("Failed to process %s: %s", src, exc)

    def _wait_for_stable(self, path: Path) -> None:
        prev_size = -1
        elapsed = 0.0
        while elapsed < _SETTLE_TIMEOUT:
            try:
                size = path.stat().st_size
            except FileNotFoundError:
                time.sleep(0.25)
                elapsed += 0.25
                continue
            if size == prev_size:
                return
            prev_size = size
            time.sleep(_SETTLE_SECONDS)
            elapsed += _SETTLE_SECONDS

    def _rebuild_index(self) -> None:
        try:
            generate_index(
                folder=self.output_folder,
                extensions=self.extensions,
                thumb_size=self.thumb_size,
                index_filename=self.index_filename,
            )
        except Exception as exc:
            logger.error("Index rebuild failed: %s", exc)



def start_watching(config: dict) -> None:
    handler = ScreenshotHandler(config)
    observer = Observer()
    observer.schedule(handler, str(handler.watch_folder), recursive=False)
    observer.start()
    logger.info("Watching: %s  (output: %s)", handler.watch_folder, handler.output_folder)
    logger.info("Press Ctrl-C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()
        logger.info("Watcher stopped.")