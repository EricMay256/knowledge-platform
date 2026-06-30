"""The common result type shared by validation, linting, and policy checks.

A `Finding` is one thing the governance layer noticed about one note (or one
changed path). Keeping a single flat type means the CLI can render and the CI
can exit-code uniformly regardless of which check produced it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    """Ordered by escalation. `ERROR` is the only severity that fails a run."""

    ERROR = "error"      # structural breakage or a hard policy violation
    WARNING = "warning"  # governance drift; safe to ship, worth fixing
    INFO = "info"        # advisory / cosmetic

    @property
    def rank(self) -> int:
        return {"error": 3, "warning": 2, "info": 1}[self.value]


@dataclass(frozen=True)
class Finding:
    path: str          # vault-relative posix path of the note (or changed file)
    severity: Severity
    rule: str          # short stable id, e.g. "unknown-type", "tags-casing"
    message: str       # human-readable detail

    def format_line(self) -> str:
        return f"{self.severity.value.upper():7} {self.path}\n    [{self.rule}] {self.message}"

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "severity": self.severity.value,
            "rule": self.rule,
            "message": self.message,
        }


def has_errors(findings: list[Finding]) -> bool:
    return any(f.severity is Severity.ERROR for f in findings)


def sort_key(f: Finding) -> tuple:
    # Errors first, then by path, then by rule — stable, deterministic output.
    return (-f.severity.rank, f.path, f.rule)
