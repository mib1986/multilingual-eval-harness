"""Turn a rubric plus annotation records into an agreement report."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence

from . import agreement


class AnnotationError(ValueError):
    """Raised when annotation records cannot be read or are malformed."""


def load_annotations(path: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AnnotationError(f"{path}:{line_no}: invalid JSON ({exc})") from exc
            for key in ("item_id", "rater", "scores"):
                if key not in record:
                    raise AnnotationError(f"{path}:{line_no}: missing '{key}'")
            if not isinstance(record["scores"], dict):
                raise AnnotationError(f"{path}:{line_no}: 'scores' must be an object")
            records.append(record)
    if not records:
        raise AnnotationError(f"{path}: no annotation records found")
    return records


def weighted_score(scores: Dict[str, int], dimensions: Sequence[Dict[str, Any]]) -> Optional[float]:
    """Weighted mean of the dimensions a rater actually scored."""
    pairs = [(float(d["weight"]), scores[d["id"]]) for d in dimensions if d["id"] in scores]
    if not pairs:
        return None
    total_weight = sum(weight for weight, _ in pairs)
    if total_weight == 0:
        return None
    return sum(weight * score for weight, score in pairs) / total_weight


def _group(records: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    items: Dict[str, Dict[str, Any]] = {}
    for record in records:
        item = items.setdefault(
            record["item_id"],
            {"lang": record.get("lang", ""), "excerpt": record.get("excerpt", ""), "raters": {}},
        )
        item["raters"][record["rater"]] = record["scores"]
    return items


def compute(
    records: Sequence[Dict[str, Any]],
    rubric: Dict[str, Any],
    spread_threshold: Optional[int] = None,
    mad_threshold: Optional[float] = None,
) -> Dict[str, Any]:
    dimensions = rubric["dimensions"]
    dim_ids = [d["id"] for d in dimensions]
    scale = rubric["scale"]
    thresholds = rubric["thresholds"]
    spread = int(spread_threshold if spread_threshold is not None else thresholds["spread"])
    mad_limit = float(mad_threshold if mad_threshold is not None else thresholds["mad"])

    items = _group(records)
    raters = sorted({record["rater"] for record in records})

    # One cell per item and dimension; values ordered by rater id for determinism.
    cells: Dict[str, Dict[str, List[int]]] = {}
    for item_id, item in items.items():
        cells[item_id] = {}
        for dim_id in dim_ids:
            values = [item["raters"][r][dim_id] for r in sorted(item["raters"]) if dim_id in item["raters"][r]]
            if values:
                cells[item_id][dim_id] = values

    all_values: List[List[int]] = []
    exact_flags: List[bool] = []
    adjacent_flags: List[bool] = []
    deviations: List[float] = []

    by_dim: Dict[str, Dict[str, Any]] = {
        dim_id: {"values": [], "exact": [], "adjacent": [], "mad": [], "scores": []}
        for dim_id in dim_ids
    }
    out_of_scale = []

    for item_id, per_dim in cells.items():
        for dim_id, values in per_dim.items():
            bucket = by_dim[dim_id]
            low, high = scale["min"], scale["max"]
            if any(v < low or v > high for v in values):
                out_of_scale.append({"item_id": item_id, "dimension": dim_id, "values": values})
            if len(values) >= 2:
                all_values.append(values)
                is_exact = agreement.all_equal(values)
                is_adjacent = agreement.within_tolerance(values, 1)
                mad = agreement.mean_abs_deviation(values) or 0.0
                exact_flags.append(is_exact)
                adjacent_flags.append(is_adjacent)
                deviations.append(mad)
                bucket["exact"].append(is_exact)
                bucket["adjacent"].append(is_adjacent)
                bucket["mad"].append(mad)
            bucket["scores"].extend(values)

    per_dim_rows = []
    for dim in dimensions:
        dim_id = dim["id"]
        bucket = by_dim[dim_id]
        per_dim_rows.append(
            {
                "id": dim_id,
                "label_zh": dim.get("label_zh", dim_id),
                "label_en": dim.get("label_en", dim_id),
                "weight": dim["weight"],
                "n_cells": len(bucket["exact"]),
                "exact_rate": agreement.rate(bucket["exact"]),
                "adjacent_rate": agreement.rate(bucket["adjacent"]),
                "mad": (sum(bucket["mad"]) / len(bucket["mad"])) if bucket["mad"] else None,
                "kappa": agreement.fleiss_kappa(
                    [cells[i][dim_id] for i in cells if dim_id in cells[i] and len(cells[i][dim_id]) >= 2]
                ),
                "mean_score": (sum(bucket["scores"]) / len(bucket["scores"])) if bucket["scores"] else None,
            }
        )

    # Per-rater behaviour: level, and distance from the item's consensus.
    rater_rows = []
    for rater in raters:
        scored = [rec for rec in records if rec["rater"] == rater]
        weighted = [weighted_score(rec["scores"], dimensions) for rec in scored]
        weighted = [w for w in weighted if w is not None]
        devs: List[float] = []
        for rec in scored:
            for dim_id in dim_ids:
                if dim_id not in rec["scores"] or item_id_missing(cells, rec["item_id"], dim_id):
                    continue
                centre = agreement.median(cells[rec["item_id"]][dim_id])
                if centre is not None and len(cells[rec["item_id"]][dim_id]) >= 2:
                    devs.append(abs(rec["scores"][dim_id] - centre))
        rater_rows.append(
            {
                "rater": rater,
                "n_scores": sum(len(rec["scores"]) for rec in scored),
                "n_items": len(scored),
                "mean_weighted": (sum(weighted) / len(weighted)) if weighted else None,
                "mean_dev": (sum(devs) / len(devs)) if devs else None,
                "max_dev": max(devs) if devs else None,
            }
        )

    # Arbitration queue: item-dimension pairs that cannot be resolved by averaging.
    queue = []
    for item_id, per_dim in cells.items():
        item = items[item_id]
        for dim_id, values in per_dim.items():
            if len(values) < 2:
                continue
            value_spread = max(values) - min(values)
            mad = agreement.mean_abs_deviation(values) or 0.0
            if value_spread < spread and mad < mad_limit:
                continue
            centre = agreement.median(values)
            raters_involved = []
            for rater in sorted(item["raters"]):
                score = item["raters"][rater].get(dim_id)
                if score is None:
                    continue
                raters_involved.append(
                    {
                        "rater": rater,
                        "score": score,
                        "deviation": abs(score - centre) if centre is not None else None,
                    }
                )
            queue.append(
                {
                    "item_id": item_id,
                    "lang": item["lang"],
                    "excerpt": item["excerpt"],
                    "dimension": dim_id,
                    "values": values,
                    "spread": value_spread,
                    "mad": mad,
                    "median": centre,
                    "raters": raters_involved,
                    "reason": "spread" if value_spread >= spread else "mad",
                }
            )
    queue.sort(key=lambda row: (row["spread"], row["mad"]), reverse=True)

    overall_kappa = agreement.fleiss_kappa(all_values)
    result = {
        "rubric": {"name": rubric.get("name"), "version": rubric.get("version")},
        "scale": scale,
        "thresholds": {"spread": spread, "mad": mad_limit},
        "n_items": len(items),
        "n_annotations": len(records),
        "n_raters": len(raters),
        "raters": raters,
        "by_lang": _count_by_lang(items),
        "overall": {
            "n_cells": len(exact_flags),
            "exact_rate": agreement.rate(exact_flags),
            "adjacent_rate": agreement.rate(adjacent_flags),
            "mad": (sum(deviations) / len(deviations)) if deviations else None,
            "kappa": overall_kappa,
        },
        "by_dimension": per_dim_rows,
        "rater_stats": rater_rows,
        "disagreements": queue,
        "out_of_scale": out_of_scale,
    }
    return result


def item_id_missing(cells: Dict[str, Dict[str, List[int]]], item_id: str, dim_id: str) -> bool:
    return item_id not in cells or dim_id not in cells[item_id]


def _count_by_lang(items: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in items.values():
        key = item["lang"] or "unknown"
        counts[key] = counts.get(key, 0) + 1
    return counts
