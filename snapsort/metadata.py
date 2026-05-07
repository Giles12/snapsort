

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image

# EXIF tag IDs
_EXIF_DATETIME_ORIGINAL = 36867  # DateTimeOriginal (preferred)
_EXIF_DATETIME = 306             # DateTime (fallback)
_EXIF_SOFTWARE = 305             # Software / app name

# Filename-pattern -> friendly app name (checked in order)
_APP_PATTERNS: List[Tuple[str, str]] = [
    (r"screenshot", "Screenshot"), 
    (r"sharex", "ShareX"),
    (r"flameshot", "Flameshot"),
    (r"greenshot", "Greenshot"),
    (r"snagit", "SnagIt"),
    (r"lightshot", "Lightshot"),
    (r"snip", "Snip&Sketch"),
    (r"gyazo", "Gyazo"),
    (r"monosnap", "Monosnap"),
    (r"chrome", "Chrome"),
    (r"firefox", "Firefox"),
    (r"msedge|edge", "Edge"),
    (r"safari", "Safari"),
    (r"teams", "Teams"),
    (r"slack", "Slack"),
    (r"zoom", "Zoom"),
    (r"discord", "Discord"),
    (r"obs", "OBS"),
]

# Filename date patterns: (regex, number_of_groups)
_DATE_PATTERNS: List[Tuple[str, int]] = [
    # Mac: Screenshot 2026-05-01 at 14.25.00
    (r"(\d{4})-(\d{2})-(\d{2}) at (\d{1,2})\.(\d{2})\.(\d{2})\s*([AP]M)", 6),
    # 2026-02-09_14-32-45 or 2026-02-09 14.32.45
    (r"(\d{4})[_\-](\d{2})[_\-](\d{2})[_\- ](\d{2})[_\-\.](\d{2})[_\-\.](\d{2})", 6),
    # 20260209_143245
    (r"(\d{4})(\d{2})(\d{2})[_\-](\d{2})(\d{2})(\d{2})", 6),
    # 2026-02-09
    (r"(\d{4})[_\-](\d{2})[_\-](\d{2})", 3),
    # 20260209
    (r"(?<!\d)(\d{4})(\d{2})(\d{2})(?!\d)", 3),
]

def extract_metadata(filepath: Path) -> Dict:
    """Return a dict with keys ``date`` (datetime) and ``app`` (str).

    Extraction order:
    1. EXIF tags (DateTimeOriginal, Software)
    2. Filename pattern matching
    3. File modification time / 'Screenshot' fallback
    """
    meta: Dict = {
        "date": None,
        "app": None,
        "original_path": filepath,
    }

    # --- EXIF -----------------------------------------------------------------
    try:
        with Image.open(filepath) as img:
            exif = img._getexif()  # returns None for non-JPEG or missing EXIF
            if exif:
                raw_date = exif.get(_EXIF_DATETIME_ORIGINAL) or exif.get(_EXIF_DATETIME)
                if raw_date:
                    meta["date"] = _parse_exif_date(raw_date)

                raw_sw = (exif.get(_EXIF_SOFTWARE) or "").strip()
                if raw_sw:
                    meta["app"] = _sanitize_app_name(raw_sw)
    except Exception:
        pass  # non-image or corrupt file; fall through to filename heuristics

    # --- Filename date --------------------------------------------------------
    if meta["date"] is None:
        meta["date"] = _date_from_filename(filepath.name)

    # --- mtime fallback -------------------------------------------------------
    if meta["date"] is None:
        meta["date"] = datetime.fromtimestamp(filepath.stat().st_mtime)

    # --- Filename app detection -----------------------------------------------
    if not meta["app"]:
        meta["app"] = _app_from_filename(filepath.name)

    if not meta["app"]:
        meta["app"] = "Screenshot"

    return meta


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_exif_date(value: str) -> Optional[datetime]:
    try:
        return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
    except (ValueError, TypeError):
        return None

def _date_from_filename(name: str) -> Optional[datetime]:
    for pattern, groups in _DATE_PATTERNS:
        m = re.search(pattern, name)
        if m:
            try:
                g = m.groups()
                if groups == 6 and len(g) == 7:  # Mac 12-hour format with AM/PM
                    nums = [int(x) for x in g[:6]]
                    am_pm = g[6]
                    h = nums[3]
                    if am_pm == 'PM' and h != 12:
                        h += 12
                    elif am_pm == 'AM' and h == 12:
                        h = 0
                    return datetime(nums[0], nums[1], nums[2], h, nums[4], nums[5])
                elif groups == 6:
                    nums = [int(x) for x in g]
                    return datetime(nums[0], nums[1], nums[2], nums[3], nums[4], nums[5])
                else:
                    nums = [int(x) for x in g]
                    return datetime(nums[0], nums[1], nums[2])
            except ValueError:
                continue
    return None


def _sanitize_app_name(name: str) -> str:
    """Strip version numbers and non-filename-safe characters from an app name."""
    # Drop trailing version strings like " 120.0.6099.129"
    name = re.sub(r"\s+\d[\d.]+.*$", "", name)
    # Keep only word characters (letters, digits, underscore)
    name = re.sub(r"[^\w]", "", name)
    name = name.strip("_")
    return name[:24] if name else ""


def _app_from_filename(name: str) -> Optional[str]:
    lower = name.lower()
    for pattern, friendly in _APP_PATTERNS:
        if re.search(pattern, lower):
            return friendly
    return None
