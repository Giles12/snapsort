

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

_CANONICAL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}_[\w]+_\d{2}-\d{2}-\d{2}(_\d+)?\.\w+$"
)


def is_canonical(filename: str) -> bool:
    return bool(_CANONICAL_RE.match(filename))


def build_name(date: datetime, app: str, ext: str, collision_index: int = 0) -> str:
    timestamp = date.strftime("%Y-%m-%d_%H-%M-%S")
    base = f"{timestamp}_{app}"
    if collision_index > 0:
        base = f"{base}_{collision_index:02d}"
    return base + ext.lower()


def rename_file(
    src: Path,
    dest_dir: Path,
    date: datetime,
    app: str,
    backup_dir: Optional[Path] = None,
) -> Path:
    if is_canonical(src.name) and src.parent.resolve() == dest_dir.resolve():
        return src  # Nothing to do

    dest_dir.mkdir(parents=True, exist_ok=True)

    ext = src.suffix
    candidate = build_name(date, app, ext)
    dest = dest_dir / candidate
    idx = 1
    while dest.exists() and dest.resolve() != src.resolve():
        candidate = build_name(date, app, ext, idx)
        dest = dest_dir / candidate
        idx += 1

    if dest.resolve() == src.resolve():
        return src  # Destination is the same file (e.g., already named correctly)

    if backup_dir is not None:
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_dest = backup_dir / src.name
        b_idx = 1
        while backup_dest.exists():
            backup_dest = backup_dir / f"{src.stem}_{b_idx:02d}{src.suffix}"
            b_idx += 1
        shutil.copy2(src, backup_dest)

    shutil.move(str(src), dest)
    return dest
