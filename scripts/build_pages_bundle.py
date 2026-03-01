#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class PathStats:
    path: str
    exists: bool
    file_count: int
    total_bytes: int


def dir_stats(path: Path) -> PathStats:
    if not path.exists():
        return PathStats(path=str(path), exists=False, file_count=0, total_bytes=0)

    if path.is_file():
        return PathStats(path=str(path), exists=True, file_count=1, total_bytes=path.stat().st_size)

    file_count = 0
    total_bytes = 0
    for p in path.rglob("*"):
        if p.is_file():
            file_count += 1
            total_bytes += p.stat().st_size
    return PathStats(path=str(path), exists=True, file_count=file_count, total_bytes=total_bytes)


def _table_exists(cur: sqlite3.Cursor, table: str) -> bool:
    row = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def _column_exists(cur: sqlite3.Cursor, table: str, column: str) -> bool:
    rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)


def collect_db_stats(db_path: Path) -> dict[str, Any]:
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    stats: dict[str, Any] = {"db_path": str(db_path), "exists": db_path.exists()}
    if not db_path.exists():
        con.close()
        return stats

    if _table_exists(cur, "podcasts"):
        stats["podcast_count"] = cur.execute("SELECT COUNT(*) FROM podcasts").fetchone()[0]
    else:
        stats["podcast_count"] = 0

    if _table_exists(cur, "episodes"):
        stats["episode_count"] = cur.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]

        date_col = None
        for candidate in ("published_at", "pub_date"):
            if _column_exists(cur, "episodes", candidate):
                date_col = candidate
                break

        if date_col:
            mn, mx = cur.execute(
                f"SELECT MIN({date_col}), MAX({date_col}) FROM episodes"
            ).fetchone()
            stats["min_date"] = mn
            stats["max_date"] = mx

        if _column_exists(cur, "episodes", "incident_type"):
            stats["incident_type_counts"] = [
                {"incident_type": r[0] or "other", "count": r[1]}
                for r in cur.execute(
                    "SELECT incident_type, COUNT(*) AS c FROM episodes GROUP BY incident_type ORDER BY c DESC"
                ).fetchall()
            ]
    else:
        stats["episode_count"] = 0

    con.close()
    return stats


def collect_dataset_stats(dataset_path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {
        "dataset_path": str(dataset_path),
        "exists": dataset_path.exists(),
        "size_bytes": dataset_path.stat().st_size if dataset_path.exists() else 0,
    }
    if not dataset_path.exists():
        return info

    try:
        payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        info["parse_error"] = str(exc)
        return info
    info["meta"] = payload.get("meta", {})
    info["counts"] = {
        "podcasts": len(payload.get("podcasts", [])),
        "episodes": len(payload.get("episodes", [])),
        "spans": len(payload.get("spans", [])),
        "places": len(payload.get("places", [])),
        "entities": len(payload.get("entities", [])),
        "clusters": len(payload.get("clusters", [])),
        "concepts": len(payload.get("concepts", [])),
        "concept_claims": len(payload.get("concept_claims", [])),
    }
    return info


def write_html_report(report_path: Path, report: dict[str, Any]) -> None:
    db_stats = report["db_stats"]
    ds_stats = report["dataset_stats"]
    b = report["bundle_stats"]

    html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Historycasts Build Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; line-height: 1.4; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
    th, td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; }}
    th {{ background: #f5f5f5; }}
    code {{ background: #f4f4f4; padding: 0.1rem 0.3rem; }}
  </style>
</head>
<body>
  <h1>Historycasts Build Report</h1>
  <p><strong>Generated:</strong> {report["generated_at_utc"]}</p>
  <p><strong>Repository:</strong> {report["repository"]}</p>
  <p><strong>Commit:</strong> <code>{report["commit_sha"]}</code></p>

  <h2>Database Stats</h2>
  <table>
    <tr><th>Metric</th><th>Value</th></tr>
    <tr><td>Podcasts</td><td>{db_stats.get("podcast_count", 0)}</td></tr>
    <tr><td>Episodes</td><td>{db_stats.get("episode_count", 0)}</td></tr>
    <tr><td>Min Date</td><td>{db_stats.get("min_date", "-")}</td></tr>
    <tr><td>Max Date</td><td>{db_stats.get("max_date", "-")}</td></tr>
  </table>

  <h2>Dataset Stats</h2>
  <table>
    <tr><th>Metric</th><th>Value</th></tr>
    <tr><td>Size (bytes)</td><td>{ds_stats.get("size_bytes", 0)}</td></tr>
    <tr><td>Podcasts</td><td>{ds_stats.get("counts", {}).get("podcasts", 0)}</td></tr>
    <tr><td>Episodes</td><td>{ds_stats.get("counts", {}).get("episodes", 0)}</td></tr>
    <tr><td>Places</td><td>{ds_stats.get("counts", {}).get("places", 0)}</td></tr>
    <tr><td>Entities</td><td>{ds_stats.get("counts", {}).get("entities", 0)}</td></tr>
    <tr><td>Clusters</td><td>{ds_stats.get("counts", {}).get("clusters", 0)}</td></tr>
  </table>

  <h2>Build Artifact Stats</h2>
  <table>
    <tr><th>Artifact</th><th>Exists</th><th>Files</th><th>Total Bytes</th></tr>
    <tr><td>webapp dist</td><td>{b["web_dist"]["exists"]}</td><td>{b["web_dist"]["file_count"]}</td><td>{b["web_dist"]["total_bytes"]}</td></tr>
    <tr><td>static_site</td><td>{b["static_site"]["exists"]}</td><td>{b["static_site"]["file_count"]}</td><td>{b["static_site"]["total_bytes"]}</td></tr>
    <tr><td>dataset file</td><td>{b["dataset_file"]["exists"]}</td><td>{b["dataset_file"]["file_count"]}</td><td>{b["dataset_file"]["total_bytes"]}</td></tr>
  </table>

  <p>Raw report JSON: <a href=\"./build-stats.json\">build-stats.json</a></p>
</body>
</html>
"""
    report_path.write_text(html, encoding="utf-8")


def write_root_index(out_dir: Path) -> None:
    html = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Historycasts Pages</title>
</head>
<body>
  <h1>Historycasts Pages</h1>
  <ul>
    <li><a href=\"./app/\">Web App Bundle</a></li>
    <li><a href=\"./static/\">Static Site Bundle</a></li>
    <li><a href=\"./data/dataset.json\">Dataset JSON</a></li>
    <li><a href=\"./reports/build-report.html\">Build Report</a></li>
    <li><a href=\"./reports/build-stats.json\">Build Stats JSON</a></li>
  </ul>
</body>
</html>
"""
    (out_dir / "index.html").write_text(html, encoding="utf-8")


def copy_tree_if_exists(src: Path, dst: Path) -> None:
    if src.exists() and src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build GitHub Pages bundle for historycasts")
    ap.add_argument("--db", required=True)
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--web-dist", required=True)
    ap.add_argument("--static-site", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo", default="unknown")
    ap.add_argument("--sha", default="unknown")
    args = ap.parse_args()

    db_path = Path(args.db)
    dataset_path = Path(args.dataset)
    web_dist = Path(args.web_dist)
    static_site = Path(args.static_site)
    out_dir = Path(args.out)

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Bundle artifacts for Pages
    copy_tree_if_exists(web_dist, out_dir / "app")
    copy_tree_if_exists(static_site, out_dir / "static")

    data_dir = out_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    if dataset_path.exists():
        shutil.copy2(dataset_path, data_dir / "dataset.json")

    reports_dir = out_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": args.repo,
        "commit_sha": args.sha,
        "db_stats": collect_db_stats(db_path),
        "dataset_stats": collect_dataset_stats(dataset_path),
        "bundle_stats": {
            "web_dist": asdict(dir_stats(web_dist)),
            "static_site": asdict(dir_stats(static_site)),
            "dataset_file": asdict(dir_stats(dataset_path)),
        },
    }

    (reports_dir / "build-stats.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_html_report(reports_dir / "build-report.html", report)
    write_root_index(out_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
