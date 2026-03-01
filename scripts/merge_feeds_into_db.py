#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from podcast_atlas.feed_merge import merge_feeds


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge multiple RSS feeds into an existing podcast DB")
    ap.add_argument("--db", required=True, help="Path to existing SQLite DB")
    ap.add_argument("--rss", action="append", required=True, help="Path to RSS feed")
    ap.add_argument("--out", required=True, help="Path to write the merged DB")
    args = ap.parse_args()

    merge_feeds(
        db_path=Path(args.db), rss_paths=[Path(p) for p in args.rss], out_path=Path(args.out)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
