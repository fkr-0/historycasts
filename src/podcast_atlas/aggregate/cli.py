from __future__ import annotations

import argparse

from .db_build import build_db


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="podcast-db", description="Build/upgrade podcast DB from RSS feeds"
    )
    ap.add_argument("--db", required=True, help="SQLite database path (created if missing)")
    ap.add_argument(
        "--rss", action="append", required=True, help="Path to RSS/XML file (repeatable)"
    )
    ap.add_argument("--gazetteer", required=True, help="Path to offline gazetteer CSV")
    ap.add_argument("--limit", type=int, default=0, help="Limit episodes per feed (0=all)")

    args = ap.parse_args()

    build_db(args.db, args.rss, args.gazetteer, limit=args.limit)


if __name__ == "__main__":
    main()
