"""Knowledge-vault contribution engine (A stage).

Public surface kept small and stable so callers (CLI now, MCP tool in B2)
depend on the service + models, not the swappable A-stage implementations.
"""

from .models import (
    Action,
    ContributionResult,
    Note,
    Policy,
    ScoredCandidate,
)
from .ports import Deduper, Store
from .service import ContributionService

__all__ = [
    "Action",
    "ContributionResult",
    "ContributionService",
    "Deduper",
    "Note",
    "Policy",
    "ScoredCandidate",
    "Store",
]
