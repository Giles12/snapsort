"""Generate a browsable HTML index with thumbnails for a screenshots folder."""

import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Tuple

from PIL import Image
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_THUMBS_SUBDIR = ".thumbs"

# Regex to extract app name from canonical SnapSort filename
_CANONICAL_APP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}_(.+?)_\d{2}-\d{2}-\d{2}"
)
_CANONICAL_DATE_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})_\S+_(\d{2})-(\d{2})-(\d{2})"
)


def generate_index(
    folder: Path,
    extensions: FrozenSet[str],
    thumb_size: Tuple[int, int],
    index_filename: str = "index.html",
) -> None:
    """Scan *folder*, regenerate thumbnails, and write the HTML index."""
    folder = Path(folder).resolve()
    thumbs_dir = folder / _THUMBS_SUBDIR
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    items: List[Dict] = []
    for img_path in sorted(folder.iterdir()):
        if not img_path.is_file():
            continue
        if img_path.suffix.lower() not in extensions:
            continue
        if img_path.name == index_filename:
            continue
        # Skip the backup folder or thumbs folder
        if img_path.parent.name in (_THUMBS_SUBDIR, ".backup"):
            continue

        thumb_rel = _ensure_thumb(img_path, thumbs_dir, thumb_size)
        date = _date_from_name(img_path.name)
        app = _app_from_name(img_path.name) or "Unknown"

        items.append(
            {
                "filename": img_path.name,
                "rel_path": img_path.name,
                "thumb_path": f"{_THUMBS_SUBDIR}/{thumb_rel}",
                "date_str": date.strftime("%Y-%m-%d") if date else "",
                "date_display": date.strftime("%Y-%m-%d %H:%M:%S") if date else "Unknown",
                "app": app,
                "size_kb": round(img_path.stat().st_size / 1024, 1),
            }
        )

    # Most-recent first
    items.sort(key=lambda x: x["date_str"], reverse=True)
    apps = sorted({i["app"] for i in items if i["app"] != "Unknown"})

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=True,
    )
    template = env.get_template("index.html.j2")
    html = template.render(
        items=items,
        apps=apps,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total=len(items),
    )

    index_path = folder / index_filename
    index_path.write_text(html, encoding="utf-8")
    logger.info("Index updated: %s  (%d files)", index_path, len(items))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_thumb(img_path: Path, thumbs_dir: Path, size: Tuple[int, int]) -> str:
    """Create thumbnail if missing; return thumb filename."""
    thumb_name = f"{img_path.stem}_thumb{img_path.suffix}"
    thumb_path = thumbs_dir / thumb_name
    if not thumb_path.exists():
        try:
            with Image.open(img_path) as img:
                img.thumbnail(size, Image.LANCZOS)
                img.save(thumb_path)
        except Exception as exc:
            logger.warning("Could not create thumbnail for %s: %s", img_path.name, exc)
            try:
                shutil.copy2(img_path, thumb_path)
            except Exception:
                pass
    return thumb_name


def _date_from_name(name: str) -> Optional[datetime]:
    m = _CANONICAL_DATE_RE.match(name)
    if m:
        try:
            g = [int(x) for x in m.groups()]
            return datetime(g[0], g[1], g[2], g[3], g[4], g[5])
        except ValueError:
            pass
    # Broader fallback patterns
    for pattern in [
        r"(\d{4})[_\-](\d{2})[_\-](\d{2})[_\- ](\d{2})[_\-\.](\d{2})[_\-\.](\d{2})",
        r"(\d{4})[_\-](\d{2})[_\-](\d{2})",
    ]:
        mm = re.search(pattern, name)
        if mm:
            g = [int(x) for x in mm.groups()]
            try:
                return datetime(*g) if len(g) == 6 else datetime(*g)
            except ValueError:
                continue
    return None


def _app_from_name(name: str) -> Optional[str]:
    m = _CANONICAL_APP_RE.match(name)
    return m.group(1) if m else None
