from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from ..static_export import export_dataset as _export_dataset
from ..static_export import write_json as _write_json


def export_dataset(db_path: Path | str) -> Dict[str, Any]:
    return _export_dataset(db_path)


def write_json(payload: Dict[str, Any], out_path: Path | str, *, minify: bool = False) -> None:
    _write_json(payload, out_path, minify=minify)
