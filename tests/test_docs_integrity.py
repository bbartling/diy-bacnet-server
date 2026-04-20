"""Sanity checks for Jekyll docs under docs/ (internal links, front matter)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def _resolve_internal_md(from_file: Path, link_target: str) -> Path | None:
    """Return expected *.md path for a sibling or relative doc link; None to skip.

    Assumptions (kept simple on purpose): no image links, no ``.html`` targets,
    targets are basename or ``basename.md`` paths, and doc bodies do not rely on
    markdown links inside fenced code blocks in ways this regex would mis-handle.
    """
    t = link_target.strip().strip('"').strip("'").split("#", 1)[0]
    if not t or t.startswith(("http://", "https://", "mailto:", "{{")):
        return None
    if t.startswith("/"):
        return None
    if t.endswith(".md"):
        return (from_file.parent / t).resolve()
    return (from_file.parent / f"{t}.md").resolve()


@pytest.mark.parametrize(
    "md_path",
    sorted(p for p in DOCS_DIR.glob("*.md") if p.name != "404.md"),
)
def test_doc_internal_links_resolve(md_path: Path):
    text = md_path.read_text(encoding="utf-8", errors="replace")
    missing: list[tuple[str, str]] = []
    for m in _MARKDOWN_LINK_RE.finditer(text):
        raw = m.group(1)
        resolved = _resolve_internal_md(md_path, raw)
        if resolved is None:
            continue
        if not resolved.is_file():
            missing.append((raw, str(resolved)))
    assert not missing, f"{md_path.name} has unresolved links: {missing}"


def test_docs_front_matter_has_no_layout_default():
    """Just the Docs + GitHub Pages use theme layout; pages should not set layout: default."""
    for md_path in DOCS_DIR.glob("*.md"):
        body = md_path.read_text(encoding="utf-8", errors="replace")
        if md_path.name == "404.md":
            continue
        assert (
            "layout: default" not in body
        ), f"{md_path.name}: remove layout: default (remote theme supplies layout)"


def test_docs_config_has_remote_theme_and_baseurl():
    cfg_text = (DOCS_DIR / "_config.yml").read_text(encoding="utf-8", errors="replace")
    config = yaml.safe_load(cfg_text)
    assert isinstance(config, dict), "_config.yml must parse to a YAML mapping"
    rt = config.get("remote_theme")
    bu = config.get("baseurl")
    assert rt, "_config.yml must set a non-empty remote_theme"
    assert "just-the-docs" in str(rt).lower()
    assert bu, "_config.yml must set a non-empty baseurl"
