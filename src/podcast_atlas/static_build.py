from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

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
        render_markdown_docs(repo_root=web_dir.parent, out_dir=web_dir / "dist" / "docs")
