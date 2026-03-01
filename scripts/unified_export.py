#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from podcast_atlas.static_export import export_dataset, write_json


def main() -> int:
    ap = argparse.ArgumentParser(description="Export a podcast DB to static JSON")
    ap.add_argument("--db", required=True, help="Path to SQLite database")
    ap.add_argument("--out", required=True, help="Output JSON file")
    ap.add_argument("--minify", action="store_true", help="Write compact JSON without indentation")
    args = ap.parse_args()

    payload = export_dataset(Path(args.db))
    write_json(payload, Path(args.out), minify=bool(args.minify))
    print(
        f"Wrote dataset with {len(payload['podcasts'])} podcasts and {len(payload['episodes'])} episodes to {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
