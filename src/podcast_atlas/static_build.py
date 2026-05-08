from __future__ import annotations

import html
import json
import shutil
import subprocess
from collections.abc import Sized
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .export.site import render_markdown_docs
from .static_export import export_dataset, write_json


def build_static(
    *, db_path: Path, dataset_out: Path, web_dir: Path, skip_web_build: bool = False
) -> None:
    """Build static artifacts: dataset JSON, web bundle, and rendered docs pages."""
    payload = export_dataset(db_path)
    write_json(payload, dataset_out)

    if not skip_web_build:
        subprocess.run(["pnpm", "build"], cwd=web_dir, check=True)
        dist_dataset = web_dir / "dist" / "dataset.json"
        dist_dataset.parent.mkdir(parents=True, exist_ok=True)
        if dataset_out.exists():
            shutil.copyfile(dataset_out, dist_dataset)
        else:
            write_json(payload, dist_dataset)
    docs_out = web_dir / "dist" / "docs"
    render_markdown_docs(repo_root=web_dir.parent, out_dir=docs_out)
    _write_build_report(db_path=db_path, dataset_out=dataset_out, payload=payload, out_dir=docs_out)


def _write_build_report(
    *, db_path: Path, dataset_out: Path, payload: dict[str, Any], out_dir: Path
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    def _count_items(value: object) -> int:
        return len(value) if isinstance(value, Sized) else 0

    counts = {
        "podcasts": _count_items(payload.get("podcasts", [])),
        "episodes": _count_items(payload.get("episodes", [])),
        "spans": _count_items(payload.get("spans", [])),
        "places": _count_items(payload.get("places", [])),
        "entities": _count_items(payload.get("entities", [])),
        "clusters": _count_items(payload.get("clusters", [])),
        "concepts": _count_items(payload.get("concepts", [])),
        "concept_claims": _count_items(payload.get("concept_claims", [])),
    }
    generated_at = datetime.now(timezone.utc).isoformat()
    db_path_str = str(db_path)
    dataset_path_str = str(dataset_out)
    report = {
        "generated_at_utc": generated_at,
        "db_path": db_path_str,
        "db_size_bytes": db_path.stat().st_size if db_path.exists() else 0,
        "dataset_path": dataset_path_str,
        "dataset_size_bytes": dataset_out.stat().st_size if dataset_out.exists() else 0,
        "counts": counts,
    }
    (out_dir / "build-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    rows = "\n".join(
        f"<tr><td>{html.escape(key)}</td><td>{value}</td></tr>" for key, value in counts.items()
    )
    page = (
        "<!doctype html>\n"
        "<html lang='en'><head><meta charset='utf-8'/>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'/>"
        "<title>Historycasts Build Report</title>"
        "<style>"
        "body{font-family:ui-sans-serif,system-ui,sans-serif;max-width:820px;margin:2rem auto;padding:0 1rem;line-height:1.5}"
        "table{border-collapse:collapse;width:100%}"
        "th,td{border:1px solid #ddd;padding:.5rem;text-align:left}"
        "th{background:#f5f5f5}"
        "code{background:#f4f4f4;padding:.1rem .3rem;border-radius:4px}"
        "</style></head><body>"
        "<h1>Historycasts Build Report</h1>"
        f"<p><strong>Generated:</strong> {html.escape(generated_at)}</p>"
        f"<p><strong>DB:</strong> <code>{html.escape(db_path_str)}</code> ({report['db_size_bytes']} bytes)</p>"
        f"<p><strong>Dataset:</strong> <code>{html.escape(dataset_path_str)}</code> ({report['dataset_size_bytes']} bytes)</p>"
        "<h2>Dataset Counts</h2>"
        "<table><tr><th>Metric</th><th>Count</th></tr>"
        f"{rows}</table>"
        "<p><a href='./build-report.json'>Raw report JSON</a></p>"
        "</body></html>"
    )
    (out_dir / "build-report.html").write_text(page, encoding="utf-8")
