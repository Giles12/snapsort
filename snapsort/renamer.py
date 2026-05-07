

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

# Files already in our canonical format — skip re-processing
_CANONICAL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}_[\w]+_\d{2}-\d{2}-\d{2}(_\d+)?\.\w+$"
)


def is_canonical(filename: str) -> bool:
    """Return True if *filename* already matches the SnapSort naming pattern."""
    return bool(_CANONICAL_RE.match(filename))


def build_name(date: datetime, app: str, ext: str, collision_index: int = 0) -> str:
    """Build the canonical filename string.

    ``collision_index`` > 0 appends a two-digit suffix to avoid clashes.
    """
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
    """Rename *src* into *dest_dir* using the canonical SnapSort name.

    Parameters
    ----------
    src:
        Original file path.
    dest_dir:
        Directory where the renamed file will be placed (created if needed).
    date:
        Datetime to embed in the filename.
    app:
        Application name to embed in the filename.
    backup_dir:
        If given, a copy of the original is saved here before renaming.

    Returns
    -------
    Path
        Path to the renamed file (or *src* unchanged if already canonical).
    """
    if is_canonical(src.name) and src.parent.resolve() == dest_dir.resolve():
        return src  # Nothing to do

    dest_dir.mkdir(parents=True, exist_ok=True)

    # Build a collision-free destination path
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

    # Backup original before moving
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
