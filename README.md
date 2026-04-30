# SnapSort

**Automated Screenshot Organizer with Metadata-Driven Renaming and Index Generation**

SnapSort monitors a screenshots folder, extracts creation-date and application metadata, auto-renames files with a standardized prefix (e.g., `2026-02-09_Chrome_14-32-45.png`), and generates a browsable HTML index page with thumbnails.

---

## Features

| Feature | Status |
|---|---|
| Real-time folder watching | ✅ |
| EXIF metadata extraction (date, software) | ✅ |
| Filename-pattern date/app fallback | ✅ |
| Canonical rename: `YYYY-MM-DD_APP_HH-MM-SS.ext` | ✅ |
| Collision-safe rename (sequence suffix) | ✅ |
| Backup originals before rename | ✅ |
| Thumbnail generation | ✅ |
| HTML index with grid + table views | ✅ |
| Search / filter by name, app, date range (JS) | ✅ |
| Date-based subfolders (optional) | ✅ |
| Cross-platform (Windows / macOS / Linux) | ✅ |

---

## Requirements

- Python 3.9+
- Dependencies in `requirements.txt`:

```
watchdog>=3.0.0
Pillow>=10.0.0
Jinja2>=3.1.0
PyYAML>=6.0
```

Install with:

```bash
pip install -r requirements.txt
```

---

## Setup

1. Clone / copy the project folder.
2. Edit `config.yaml` to point `watch_folder` at your screenshots directory.
3. Run any command below.

---

## Usage

```bash
# Watch folder in real time (Ctrl-C to stop)
python main.py watch

# Batch-rename all existing screenshots in a folder
python main.py rename

# Generate / regenerate the HTML index
python main.py index

# Override the watched folder inline
python main.py watch ~/Pictures/Screenshots
python main.py rename ~/Pictures/Screenshots
python main.py index  ~/Pictures/Screenshots

# Use a custom config file
python main.py -c /path/to/myconfig.yaml watch
```

---

## Configuration (`config.yaml`)

```yaml
watch_folder: "~/Screenshots"   # Folder to monitor
output_folder: ""               # Leave empty = rename in-place
backup: true                    # Copy originals to backup_folder before rename
backup_folder: ".backup"        # Relative to watch_folder (or absolute path)
thumb_size: [200, 150]          # Thumbnail dimensions [width, height]
index_filename: "index.html"    # Name of the generated index
date_subfolders: false          # Organise into YYYY/MM-DD subfolders
image_extensions:
  - ".png"
  - ".jpg"
  - ".jpeg"
  - ".gif"
  - ".bmp"
  - ".webp"
  - ".tiff"
```

---

## Naming Convention

```
2026-02-09_Chrome_14-32-45.png
│           │      │
│           │      └── HH-MM-SS (time)
│           └───────── App name (from EXIF Software tag or filename heuristic)
└───────────────────── YYYY-MM-DD (from EXIF DateTimeOriginal or filename/mtime)
```

Collision handling appends a two-digit suffix: `…_14-32-45_01.png`.

---

## Project Structure

```
snapsort/
├── snapsort/
│   ├── __init__.py
│   ├── metadata.py      # EXIF + filename date/app extraction
│   ├── renamer.py       # Canonical rename + collision handling
│   ├── watcher.py       # watchdog real-time event handler
│   ├── indexer.py       # Thumbnail + HTML index generator
│   └── templates/
│       └── index.html.j2
├── config.yaml
├── main.py              # CLI entry point
└── requirements.txt
```

---

## Deliverables (per project spec)

- Git repository with full source
- CLI executable (`main.py`)
- `config.yaml` (setup & demo ready)
- Sample watch folder: point `watch_folder` at any directory containing screenshots
- Final report (see paper)
