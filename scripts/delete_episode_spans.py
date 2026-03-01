#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from podcast_atlas.curation import delete_episode_spans


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Delete time_spans rows for an episode (and dependent span links)."
    )
    ap.add_argument("--db", required=True, help="Path to SQLite DB")
    ap.add_argument("--episode-id", required=True, type=int, help="Episode id")
    ap.add_argument(
        "--keep-span-id",
        action="append",
        default=[],
        type=int,
        help="Span id to keep (repeatable)",
    )
    args = ap.parse_args()

    result = delete_episode_spans(
        Path(args.db), episode_id=int(args.episode_id), keep_span_ids=args.keep_span_id
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
