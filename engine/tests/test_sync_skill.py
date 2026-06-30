"""The skill-sync helper's pure transform (render_portable)."""

from __future__ import annotations

from scripts.sync_skill import render_portable

SAMPLE = """\
---
name: knowledge-vault
description: >-
  Do a thing. Use when X. Do NOT use for Y.
---

# Body Heading

Some guidance with an arrow → and an em dash —.
"""


def test_portable_strips_frontmatter_and_surfaces_description():
    out = render_portable(SAMPLE)
    # Claude trigger frontmatter is gone...
    assert "name: knowledge-vault" not in out
    assert not out.lstrip().startswith("---")
    # ...the description is surfaced as readable context...
    assert "## When to use" in out
    assert "Do a thing. Use when X. Do NOT use for Y." in out
    # ...the body is preserved (including non-ASCII)...
    assert "# Body Heading" in out
    assert "→" in out and "—" in out
    # ...and there's a provenance header pointing back at the source.
    assert "scripts/sync_skill.py" in out


def test_portable_handles_missing_frontmatter():
    out = render_portable("# Just a body\n\ntext")
    assert "# Just a body" in out
    assert "## When to use" not in out  # no description to surface
