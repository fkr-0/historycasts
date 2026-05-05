"""Export/render subsystem.

This package defines static dataset/site export helpers used by CLI orchestration.
"""

from .cluster_metrics import compute_cluster_metrics

__all__ = [
    "export_dataset",
    "write_json",
    "compute_cluster_metrics",
    "build_static_bundle",
    "render_markdown_docs",
]


def export_dataset(*args, **kwargs):
    from .dataset import export_dataset as _export_dataset

    return _export_dataset(*args, **kwargs)


def write_json(*args, **kwargs):
    from .dataset import write_json as _write_json

    return _write_json(*args, **kwargs)


def build_static_bundle(*args, **kwargs):
    from .site import build_static_bundle as _build_static_bundle

    return _build_static_bundle(*args, **kwargs)


def render_markdown_docs(*args, **kwargs):
    from .site import render_markdown_docs as _render_markdown_docs

    return _render_markdown_docs(*args, **kwargs)
