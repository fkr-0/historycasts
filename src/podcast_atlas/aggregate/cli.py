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
    ap.add_argument(
        "--year-max",
        type=int,
        default=None,
        help="Maximum allowed year for spans; later dates are pruned in postprocess",
    )
    ap.add_argument(
        "--disable-heuristic-review",
        action="store_true",
        help="Disable insertion of locked nondet heuristic review overrides",
    )

    args = ap.parse_args()

    kwargs = {
        "limit": args.limit,
        "enable_heuristic_review": not bool(args.disable_heuristic_review),
    }
    if args.year_max is not None:
        kwargs["year_max"] = int(args.year_max)
    build_db(args.db, args.rss, args.gazetteer, **kwargs)


if __name__ == "__main__":
    main()
