"""Human-vault Map-of-Content rendering."""

from __future__ import annotations

from vault_governance.moc import render_moc


class _Rec:
    def __init__(self, rel_path: str):
        self.rel_path = rel_path


def test_render_moc_groups_by_subfolder_and_stamps():
    recs = [
        _Rec("Human/Home.md"),                              # directly in folder
        _Rec("Human/03 Projects/Project - X.md"),
        _Rec("Human/03 Projects/Project - Y/Detail.md"),    # nested -> counts under "03 Projects"
        _Rec("Human/04 Areas/Area - Z.md"),
    ]
    out = render_moc("Human", recs,
                     created="2026-01-01T00:00:00Z", now="2026-02-02T00:00:00Z")

    assert out.startswith("---\nType: MoC\n")
    assert "CreatedAt: 2026-01-01T00:00:00Z" in out
    assert "LastUpdated: 2026-02-02T00:00:00Z" in out
    # Root note listed unsectioned; subfolders become sections.
    assert "- [[Home]]" in out
    assert "## 03 Projects (2)" in out
    assert "[[Project - X]]" in out and "[[Detail]]" in out
    assert "## 04 Areas (1)" in out


def test_render_moc_preserves_created_and_handles_empty():
    out = render_moc("Human/07 People", [], now="2026-02-02T00:00:00Z")
    assert "# 07 People" in out
    assert "_0 notes._" in out
    # created defaults to now when not supplied.
    assert "CreatedAt: 2026-02-02T00:00:00Z" in out
