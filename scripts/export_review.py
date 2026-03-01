from __future__ import annotations

import json
from pathlib import Path

from podcast_atlas.db import Database


def main() -> int:
    db_path = Path("active.db")
    db = Database(db_path)
    eps = db.list_episodes()

    lines = []
    lines.append("# Manual review sheet (sample fixtures)")
    lines.append("")
    lines.append(
        "This file is generated from the SQLite DB. For real feeds, re-run ingestion then regenerate."
    )
    lines.append("")

    for e in eps:
        persons = json.loads(e.get("persons_json") or "[]")
        links = json.loads(e.get("links_json") or "[]")
        lines.append(f"## {e['guid']} — {e['title']}")
        lines.append("")
        lines.append(f"- podcast: {e['podcast_id']}")
        lines.append(f"- published_at: {e['published_at']}")
        lines.append(f"- incident_type: {e.get('incident_type')}")
        lines.append(
            f"- primary_time: {e.get('primary_time_kind')} {e.get('primary_time_year') or ''}{(' ' + str(e.get('primary_time_start_year')) + '-' + str(e.get('primary_time_end_year'))) if e.get('primary_time_kind') == 'range' else ''}"
        )
        lines.append(
            f"- primary_location: {e.get('primary_location_name')} ({e.get('primary_location_country')}) [{e.get('primary_location_lat')},{e.get('primary_location_lon')}]"
            if e.get("primary_location_name")
            else "- primary_location: —"
        )
        lines.append(f"- persons: {', '.join(persons) if persons else '—'}")
        lines.append(f"- links: {', '.join(links) if links else '—'}")
        lines.append("")

    Path("data").mkdir(exist_ok=True)
    Path("data/manual_review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
