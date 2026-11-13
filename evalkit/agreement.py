"""Agreement metrics for rubric-based evaluation.

Every function takes plain Python data: one list of integer scores per item,
in the rubric scale. Missing ratings are simply absent from the list, so
varying rater counts per item are supported without a placeholder value.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence


def median(values: Sequence[float]) -> Optional[float]:
    """Median of the given scores; None for an empty sequence."""
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def all_equal(values: Sequence[int]) -> bool:
    """True when every rater produced the same score."""
    return bool(values) and len(set(values)) == 1


def within_tolerance(values: Sequence[int], tol: int = 1) -> bool:
    """True when the spread between the highest and lowest score is <= tol."""
    return bool(values) and (max(values) - min(values)) <= tol


def mean_abs_deviation(values: Sequence[int]) -> Optional[float]:
    """Mean distance of each score from the median score of the item."""
    centre = median(values)
    if centre is None:
        return None
    return sum(abs(v - centre) for v in values) / len(values)


def fleiss_kappa(items: Sequence[Sequence[int]]) -> Optional[float]:
    """Fleiss' kappa over items, generalised to a varying rater count per item.

    ``items`` is one list of scores per item. Items with fewer than two
    ratings are skipped. Returns None when the expected agreement is 1.0
    (kappa undefined) or when there is nothing to compare.
    """
    usable = [list(v) for v in items if len(v) >= 2]
    if not usable:
        return None

    categories = sorted({score for values in usable for score in values})
    if len(categories) < 2:
        # Every rating sits in the same category: agreement is total.
        return 1.0

    observed = []
    category_totals: Dict[int, int] = {c: 0 for c in categories}
    total_ratings = 0

    for values in usable:
        m = len(values)
        counts = {c: 0 for c in categories}
        for score in values:
            counts[score] += 1
            category_totals[score] += 1
        total_ratings += m
        # P_i: how much the raters of this item agree, corrected for chance
        observed.append((sum(c * c for c in counts.values()) - m) / (m * (m - 1)))

    p_observed = sum(observed) / len(observed)
    p_expected = sum((n / total_ratings) ** 2 for n in category_totals.values())

    if abs(1.0 - p_expected) < 1e-12:
        return None
    return (p_observed - p_expected) / (1.0 - p_expected)


def rate(flags: Sequence[bool]) -> Optional[float]:
    """Share of True values, or None for an empty sample."""
    if not flags:
        return None
    return sum(1 for f in flags if f) / len(flags)
