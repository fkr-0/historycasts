#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from podcast_atlas.metadata_merge import merge_handcrafted_metadata


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Merge handcrafted metadata from res/res.json into a SQLite DB as protected rows"
    )
    ap.add_argument("--db", required=True, help="Path to SQLite DB")
    ap.add_argument("--res-json", default="res/res.json", help="Path to handcrafted metadata JSON")
    ap.add_argument(
        "--no-update-best",
        action="store_true",
        help="Do not update episodes.best_span_id/best_place_id when inserting handcrafted rows",
    )
    args = ap.parse_args()

    stats = merge_handcrafted_metadata(
        db_path=Path(args.db),
        res_json_path=Path(args.res_json),
        update_episode_best_refs=not bool(args.no_update_best),
    )
    print(
        "merge-res-metadata complete: "
        f"episodes_seen={stats['episodes_seen']} "
        f"episodes_missing={stats['episodes_missing']} "
        f"timespans_inserted={stats['timespans_inserted']} "
        f"places_inserted={stats['places_inserted']} "
        f"entities_inserted={stats['entities_inserted']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
