from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

BAD_PLACE_NAMES = {
    "apple",
    "instagram",
    "campfirefm!",
    "folgen",
    "new",
    "beginn",
    "vergessenheit",
}
BAD_ENTITY_NAMES = {
    "apple podcasts",
    "erwähnte folgen",
    "podcastplattform panoptikum",
    "im jahr",
    "vielen dank",
    "eine geschichte",
    "in der folge",
}
BAD_KEYWORD_MARKERS = [
    "apple podcasts",
    "podcastplattform panoptikum",
    "freuen uns wenn",
    "acast",
    "privacy",
    "hosted on",
    "podcasthörer",
    "instagram",
]
BOILERPLATE_LINE_MARKERS = [
    "apple podcasts",
    "podcastplattform panoptikum",
    "acast.com/privacy",
    "podcasthörer",
    "freundinnen und freunden",
    "kolleginnen und kollegen",
    "nachbarinnen und nachbarn",
]
AD_LINK_MARKERS = [
    "instagram.com",
    "tiktok.com",
    "facebook.com",
    "linktr.ee",
    "podcasts.apple.com",
    "open.spotify.com",
    "acast.com",
]
SOURCE_LINK_MARKERS = [
    "wikipedia.org",
    "wikidata.org",
    "archive.org",
    "doi.org",
    "jstor.org",
    "books.google.",
    "cambridge.org",
    "oxfordacademic.com",
    "degruyter.com",
    "springer.com",
]


def _domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def _is_ad_link(url: str) -> bool:
    u = url.lower()
    return any(m in u for m in AD_LINK_MARKERS)


def _is_source_link(url: str) -> bool:
    u = url.lower()
    return any(m in u for m in SOURCE_LINK_MARKERS)


def build_report(db_path: Path, sample: int) -> dict[str, object]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    places = cur.execute(
        """
        SELECT p.id, p.episode_id, e.title, p.name_raw, p.place_kind
        FROM places p
        JOIN episodes e ON e.id = p.episode_id
        """
    ).fetchall()
    bad_places = [
        dict(r)
        for r in places
        if r["place_kind"] == "city"
        and (
            r["name_raw"].lower() in BAD_PLACE_NAMES
            or r["name_raw"].lower().startswith("gag")
            or r["name_raw"].lower().startswith("feedgag")
        )
    ]

    entities = cur.execute(
        """
        SELECT en.id, en.episode_id, ep.title, en.name, en.kind
        FROM entities en
        JOIN episodes ep ON ep.id = en.episode_id
        """
    ).fetchall()
    bad_entities = [dict(r) for r in entities if r["name"].lower() in BAD_ENTITY_NAMES]

    keyword_rows = cur.execute(
        """
        SELECT k.id, k.phrase, COUNT(ek.episode_id) AS episode_count
        FROM keywords k
        LEFT JOIN episode_keywords ek ON ek.keyword_id = k.id
        GROUP BY k.id, k.phrase
        ORDER BY episode_count DESC
        """
    ).fetchall()
    bad_keywords = [
        dict(r)
        for r in keyword_rows
        if any(m in r["phrase"].lower() for m in BAD_KEYWORD_MARKERS)
    ]

    links = cur.execute(
        """
        SELECT l.id, l.episode_id, e.title, l.url, l.link_type
        FROM links l
        JOIN episodes e ON e.id = l.episode_id
        """
    ).fetchall()
    domain_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"count": 0, "ad_suspect": 0, "source_suspect": 0}
    )
    link_samples: list[dict[str, object]] = []
    for r in links:
        url = r["url"] or ""
        dom = _domain(url)
        if not dom:
            continue
        domain_stats[dom]["count"] += 1
        ad = _is_ad_link(url)
        source = _is_source_link(url)
        if ad:
            domain_stats[dom]["ad_suspect"] += 1
        if source:
            domain_stats[dom]["source_suspect"] += 1
        if ad and len(link_samples) < sample:
            link_samples.append(
                {
                    "id": r["id"],
                    "episode_id": r["episode_id"],
                    "title": r["title"],
                    "url": url,
                    "link_type": r["link_type"],
                    "reason": "ad-suspect-domain",
                }
            )

    top_domains = sorted(
        (
            {
                "domain": d,
                "count": v["count"],
                "ad_suspect": v["ad_suspect"],
                "source_suspect": v["source_suspect"],
            }
            for d, v in domain_stats.items()
        ),
        key=lambda x: x["count"],
        reverse=True,
    )[:60]

    eps = cur.execute("SELECT id, title, description_pure FROM episodes").fetchall()
    desc_candidates: list[dict[str, object]] = []
    for r in eps:
        text = r["description_pure"] or ""
        lines = []
        for ln in text.splitlines():
            if any(m in ln.casefold() for m in BOILERPLATE_LINE_MARKERS):
                lines.append(ln.strip())
        if lines:
            desc_candidates.append(
                {
                    "episode_id": r["id"],
                    "title": r["title"],
                    "matched_lines": lines[:5],
                }
            )
    con.close()

    return {
        "db_path": str(db_path),
        "counts": {
            "bad_places": len(bad_places),
            "bad_entities": len(bad_entities),
            "bad_keywords": len(bad_keywords),
            "description_candidates": len(desc_candidates),
            "ad_link_samples": len(link_samples),
        },
        "bad_places": bad_places[:sample],
        "bad_entities": bad_entities[:sample],
        "bad_keywords": bad_keywords[:sample],
        "link_domain_summary": top_domains,
        "ad_link_samples": link_samples,
        "description_candidates": desc_candidates[:sample],
    }


def write_markdown(report: dict[str, object], out_path: Path) -> None:
    c = report["counts"]
    lines = [
        "# Data Quality Review",
        "",
        f"- DB: `{report['db_path']}`",
        f"- Bad places (sampled): {c['bad_places']}",
        f"- Bad entities (sampled): {c['bad_entities']}",
        f"- Bad keywords (sampled): {c['bad_keywords']}",
        f"- Description candidates (sampled): {c['description_candidates']}",
        "",
        "## Suspicious places",
    ]
    for r in report["bad_places"]:
        lines.append(
            f"- place_id={r['id']} episode_id={r['episode_id']} kind={r['place_kind']} name=`{r['name_raw']}` | {r['title']}"
        )

    lines += ["", "## Suspicious entities"]
    for r in report["bad_entities"]:
        lines.append(
            f"- entity_id={r['id']} episode_id={r['episode_id']} kind={r['kind']} name=`{r['name']}` | {r['title']}"
        )

    lines += ["", "## Suspicious keywords"]
    for r in report["bad_keywords"]:
        lines.append(
            f"- keyword_id={r['id']} phrase=`{r['phrase']}` episode_count={r['episode_count']}"
        )

    lines += ["", "## Link domain summary (top)"]
    for r in report["link_domain_summary"][:30]:
        lines.append(
            f"- `{r['domain']}` count={r['count']} ad_suspect={r['ad_suspect']} source_suspect={r['source_suspect']}"
        )

    lines += ["", "## Description boilerplate candidates"]
    for r in report["description_candidates"]:
        lines.append(f"- episode_id={r['episode_id']} | {r['title']}")
        for ln in r["matched_lines"]:
            lines.append(f"  - {ln}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate reviewable data-quality candidates from SQLite.")
    ap.add_argument("--db", default="active.db", help="Path to SQLite DB")
    ap.add_argument("--out", default="data/data_quality_review.md", help="Markdown output path")
    ap.add_argument(
        "--json-out", default="data/data_quality_review.json", help="JSON output path"
    )
    ap.add_argument("--sample", type=int, default=80, help="Max rows per section")
    ns = ap.parse_args()

    report = build_report(Path(ns.db), sample=int(ns.sample))
    out_md = Path(ns.out)
    out_json = Path(ns.json_out)
    write_markdown(report, out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_md} and {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
