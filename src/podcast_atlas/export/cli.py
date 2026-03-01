from __future__ import annotations

import argparse
from pathlib import Path

from .dataset import export_dataset, write_json


def main() -> None:
    ap = argparse.ArgumentParser(description="Export dataset JSON from SQLite")
    ap.add_argument("--db", required=True, help="Path to SQLite DB")
    ap.add_argument("--out", required=True, help="Output dataset JSON path")
    ap.add_argument("--minify", action="store_true", help="Write compact JSON")
    args = ap.parse_args()

    payload = export_dataset(Path(args.db))
    write_json(payload, Path(args.out), minify=bool(args.minify))


if __name__ == "__main__":
    main()
