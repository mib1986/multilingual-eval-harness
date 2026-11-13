"""Loading and validating a rubric definition."""

from __future__ import annotations

import json
from typing import Any, Dict, List

WEIGHT_TOLERANCE = 0.01


class RubricError(ValueError):
    """Raised when a rubric file is structurally unusable."""


def load_rubric(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise RubricError(f"{path}: invalid JSON ({exc})") from exc
    return validate(data, source=path)


def validate(data: Dict[str, Any], source: str = "<rubric>") -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise RubricError(f"{source}: top level must be an object")

    dimensions = data.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        raise RubricError(f"{source}: 'dimensions' must be a non-empty list")

    seen: List[str] = []
    total = 0.0
    for index, dim in enumerate(dimensions):
        if not isinstance(dim, dict):
            raise RubricError(f"{source}: dimension #{index + 1} must be an object")
        dim_id = dim.get("id")
        if not dim_id or not isinstance(dim_id, str):
            raise RubricError(f"{source}: dimension #{index + 1} needs a string 'id'")
        if dim_id in seen:
            raise RubricError(f"{source}: duplicate dimension id '{dim_id}'")
        seen.append(dim_id)
        weight = dim.get("weight")
        if not isinstance(weight, (int, float)) or weight < 0:
            raise RubricError(f"{source}: dimension '{dim_id}' needs a non-negative numeric 'weight'")
        total += float(weight)

    if abs(total - 1.0) > WEIGHT_TOLERANCE:
        raise RubricError(f"{source}: dimension weights must sum to 1.0, got {total:.3f}")

    scale = data.get("scale") or {}
    low, high = scale.get("min"), scale.get("max")
    if not isinstance(low, int) or not isinstance(high, int) or high <= low:
        raise RubricError(f"{source}: 'scale' needs integer 'min' and 'max' with max > min")

    thresholds = data.get("thresholds") or {}
    thresholds.setdefault("spread", 2)
    thresholds.setdefault("mad", 0.75)
    data["scale"] = {"min": low, "max": high}
    data["thresholds"] = thresholds
    data.setdefault("name", "unnamed-rubric")
    data.setdefault("version", "0.0.0")
    return data
