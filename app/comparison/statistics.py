"""Computes summary statistics from a completed diff."""
from __future__ import annotations

from typing import List

from app.core.enums import DifferenceType
from app.core.models import Difference, DifferenceStatistics


def compute_statistics(differences: List[Difference]) -> DifferenceStatistics:
    added = sum(1 for d in differences if d.change_type == DifferenceType.ADDED)
    removed = sum(1 for d in differences if d.change_type == DifferenceType.REMOVED)
    modified = sum(1 for d in differences if d.change_type == DifferenceType.MODIFIED)
    unchanged = sum(1 for d in differences if d.change_type == DifferenceType.UNCHANGED)
    return DifferenceStatistics(
        lines_compared=len(differences),
        added=added,
        removed=removed,
        modified=modified,
        unchanged=unchanged,
    )
