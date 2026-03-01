from __future__ import annotations

import html
import re
import subprocess
from pathlib import Path
from typing import Iterable

from .dataset import export_dataset, write_json

_DEF_DOCS = ["README.md", "CHANGELOG.md", "ARCHITECTURE.md"]


def _md_to_html(md_text: str, title: str) -> str:
    lines = md_text.splitlines()
    out: list[str] = []
    in_code = False
    code_lines: list[str] = []
    code_lang = ""

    def flush_code_block() -> None:
        nonlocal code_lines, code_lang
        if not code_lines and not code_lang:
            return
        safe_lang = re.sub(r"[^a-z0-9_+-]", "", code_lang.lower()) or "text"
        escaped_code = "\n".join(html.escape(code_line) for code_line in code_lines)
        out.append(
            "<figure class='code-block'>"
            f"<figcaption>{html.escape(safe_lang)}</figcaption>"
            f"<pre><code class='language-{safe_lang}'>{escaped_code}</code></pre>"
            "</figure>"
        )
        code_lines = []
        code_lang = ""

    for line in lines:
        if line.startswith("```"):
            if not in_code:
                code_lang = line[3:].strip().split(maxsplit=1)[0] if line[3:].strip() else ""
                code_lines = []
                in_code = True
            else:
                flush_code_block()
                in_code = False
            continue
        if in_code:
            code_lines.append(line)
            continue

        if line.startswith("### "):
            out.append(f"<h3>{html.escape(line[4:])}</h3>")
            continue
        if line.startswith("## "):
            out.append(f"<h2>{html.escape(line[3:])}</h2>")
            continue
        if line.startswith("# "):
            out.append(f"<h1>{html.escape(line[2:])}</h1>")
            continue
        if line.startswith("- "):
            out.append(f"<li>{html.escape(line[2:])}</li>")
            continue
        if line.strip():
            txt = html.escape(line.strip())
            txt = re.sub(r"`([^`]+)`", r"<code>\1</code>", txt)
            out.append(f"<p>{txt}</p>")

    if in_code:
        flush_code_block()

    body = "\n".join(out)
    return (
        "<!doctype html>\n"
        "<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{html.escape(title)}</title>"
        "<style>"
        ":root{--bg:#241c38;--surface:#302548;--surface-2:#1b142b;--text:#ece8f7;--muted:#c8bbdc;--accent:#a490c2;--border:rgba(164,144,194,0.3)}"
        "body{font-family:'IBM Plex Sans','Space Grotesk',ui-sans-serif,system-ui,sans-serif;max-width:920px;margin:26px auto;padding:0 16px;line-height:1.6;color:var(--text);background:linear-gradient(160deg,var(--surface-2),var(--bg)) fixed}"
        "h1,h2,h3{font-family:'Space Grotesk','IBM Plex Sans',ui-sans-serif,system-ui,sans-serif;letter-spacing:.01em}"
        "a{color:#c6b5df}"
        "p,li{color:var(--text)}"
        "li{margin-left:20px}"
        "code{background:rgba(164,144,194,0.2);padding:1px 6px;border-radius:6px;border:1px solid var(--border)}"
        ".code-block{margin:14px 0 18px;border:1px solid var(--border);border-radius:10px;background:var(--surface)}"
        ".code-block figcaption{padding:6px 10px;border-bottom:1px solid var(--border);font:600 12px/1.2 'Space Grotesk','IBM Plex Sans',ui-sans-serif,sans-serif;color:var(--muted);text-transform:lowercase;letter-spacing:.04em}"
        "pre{margin:0;background:transparent;color:var(--text);padding:12px;border-radius:0 0 10px 10px;overflow:auto}"
        "pre code{display:block;padding:0;border:none;background:transparent;border-radius:0;color:inherit;white-space:pre}"
        "</style>"
        "</head><body>"
        f"{body}"
        "</body></html>"
    )


def render_markdown_docs(
    *, repo_root: Path, out_dir: Path, docs: Iterable[str] | None = None
) -> list[Path]:
    docs = list(docs) if docs is not None else list(_DEF_DOCS)
    out_dir.mkdir(parents=True, exist_ok=True)

    rendered: list[Path] = []
    for rel in docs:
        src = repo_root / rel
        if not src.exists() or not src.is_file():
            continue
        html_name = src.stem.lower() + ".html"
        out = out_dir / html_name
        out.write_text(_md_to_html(src.read_text(encoding="utf-8"), src.name), encoding="utf-8")
        rendered.append(out)
    return rendered


def build_static_bundle(
    *,
    db_path: Path,
    dataset_out: Path,
    web_dir: Path,
    skip_web_build: bool = False,
    render_docs: bool = True,
    docs_out_subdir: str = "docs",
) -> None:
    payload = export_dataset(db_path)
    write_json(payload, dataset_out)

    if not skip_web_build:
        subprocess.run(["pnpm", "build"], cwd=web_dir, check=True)

    if render_docs:
        repo_root = web_dir.parent
        docs_out = web_dir / "dist" / docs_out_subdir
        render_markdown_docs(repo_root=repo_root, out_dir=docs_out)
