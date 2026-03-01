from __future__ import annotations

from podcast_atlas.export.site import _md_to_html


def test_md_to_html_renders_fenced_code_without_leading_blank_line() -> None:
    md = "```bash\necho hello\n```\n"

    rendered = _md_to_html(md, "README.md")

    assert "<figcaption>bash</figcaption>" in rendered
    assert "<code class='language-bash'>echo hello</code>" in rendered
    assert "<code class='language-bash'>\n" not in rendered


def test_md_to_html_pre_code_styles_do_not_override_block_code_background() -> None:
    rendered = _md_to_html("`inline`\n\n```python\nprint('x')\n```", "README.md")

    assert "code{background:rgba(164,144,194,0.2);" in rendered
    assert "pre code{display:block;padding:0;border:none;background:transparent;" in rendered
