#!/usr/bin/env python3
"""SnapSort CLI — Automated Screenshot Organizer.

Commands
--------
  watch   Monitor a folder in real time and auto-rename new screenshots.
  rename  Batch-rename all existing screenshots in a folder.
  index   Generate (or regenerate) the HTML browsing index.

Usage
-----
  python main.py watch
  python main.py rename ~/Screenshots
  python main.py index  ~/Screenshots
  python main.py -c /path/to/custom.yaml watch
"""

import argparse
import logging
import sys
import platform  
from pathlib import Path
from typing import FrozenSet

import yaml


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _default_watch_folder() -> str:        
    system = platform.system()
    if system == "Darwin":
        return "~/Desktop"
    elif system == "Windows":
        return "~/Pictures/Screenshots"
    else:
        return "~/Pictures"

def _load_config(config_path: str) -> dict:
    p = Path(config_path)
    if not p.exists():
        print(f"[error] Config file not found: {p}", file=sys.stderr)
        sys.exit(1)
    with open(p, "r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}

    if not config.get("watch_folder"):
        config["watch_folder"] = _default_watch_folder()

    return config

def _extensions(config: dict) -> FrozenSet[str]:
    return frozenset(
        ext.lower()
        for ext in config.get(
            "image_extensions", [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]
        )
    )


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def cmd_watch(args: argparse.Namespace) -> None:
    from snapsort.watcher import start_watching

    config = _load_config(args.config)
    if args.folder:
        config["watch_folder"] = args.folder
    start_watching(config)


def cmd_rename(args: argparse.Namespace) -> None:
    from snapsort.metadata import extract_metadata
    from snapsort.renamer import is_canonical, rename_file

    config = _load_config(args.config)
    folder = Path(args.folder or config.get("watch_folder", ".")).expanduser()
    if not folder.is_dir():
        print(f"[error] Folder not found: {folder}", file=sys.stderr)
        sys.exit(1)

    output = Path(config.get("output_folder") or folder).expanduser()
    backup_dir = None
    if config.get("backup"):
        bp = config.get("backup_folder", ".backup")
        backup_dir = (
            Path(bp).expanduser() if Path(bp).is_absolute() else folder / bp
        )

    date_subfolders: bool = bool(config.get("date_subfolders", False))
    extensions = _extensions(config)

    files = [f for f in sorted(folder.iterdir()) if f.is_file() and f.suffix.lower() in extensions]
    if not files:
        print("No image files found in:", folder)
        return

    renamed = skipped = errors = 0
    for fp in files:
        if is_canonical(fp.name) and fp.parent.resolve() == output.resolve():
            skipped += 1
            continue
        try:
            meta = extract_metadata(fp)
            dest_dir = output
            if date_subfolders:
                dest_dir = output / meta["date"].strftime("%Y/%m-%d")
            new_path = rename_file(fp, dest_dir, meta["date"], meta["app"], backup_dir)
            if new_path != fp:
                print(f"  {fp.name}  ->  {new_path.name}")
                renamed += 1
            else:
                skipped += 1
        except Exception as exc:
            print(f"  [error] {fp.name}: {exc}", file=sys.stderr)
            errors += 1

    print(
        f"\nDone — renamed: {renamed}, skipped: {skipped}, errors: {errors}"
        f"  (total: {len(files)})"
    )


def cmd_index(args: argparse.Namespace) -> None:
    from snapsort.indexer import generate_index

    config = _load_config(args.config)
    folder = Path(args.folder or config.get("watch_folder", ".")).expanduser()
    if not folder.is_dir():
        print(f"[error] Folder not found: {folder}", file=sys.stderr)
        sys.exit(1)

    thumb_size = tuple(config.get("thumb_size", [200, 150]))
    index_filename = config.get("index_filename", "index.html")
    generate_index(folder, _extensions(config), thumb_size, index_filename)
    print(f"Index written to: {folder / index_filename}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="snapsort",
        description="SnapSort — Automated Screenshot Organizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        metavar="FILE",
        help="YAML config file (default: config.yaml)",
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # watch
    p_watch = sub.add_parser("watch", help="Monitor folder for new screenshots in real time")
    p_watch.add_argument("folder", nargs="?", help="Folder to watch (overrides config)")
    p_watch.set_defaults(func=cmd_watch)

    # rename
    p_rename = sub.add_parser("rename", help="Batch-rename existing screenshots")
    p_rename.add_argument("folder", nargs="?", help="Folder to process (overrides config)")
    p_rename.set_defaults(func=cmd_rename)

    # index
    p_index = sub.add_parser("index", help="Generate HTML browsing index")
    p_index.add_argument("folder", nargs="?", help="Folder to index (overrides config)")
    p_index.set_defaults(func=cmd_index)

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )

    args.func(args)


if __name__ == "__main__":
    main()
