"""
Coarse-grained rounding applied before any value leaves an agent, so a
counterpart can't reverse-engineer exact internal thresholds.

Field-aware on purpose: a single universal bucket size will silently zero
out small-scale fields (e.g. rounding inspection_level=4 to the nearest 10
gives 0). Each field gets a bucket sized to its own scale.
"""
import math
from typing import Dict

from .intent_state import IntentState

# Explicit buckets for fields we know about in this domain set.
FIELD_BUCKETS = {
    "latency_ms": 10,
    "bandwidth_mbps": 5,
    "inspection_level": 1,
    "access_level": 1,
    "risk_score": 1,
    "quarantine_minutes": 5,
}

PRIORITY_BUCKETS = [0.2, 0.4, 0.6, 0.8, 1.0]


def _bucket_for(field_name: str, value: float) -> float:
    if field_name in FIELD_BUCKETS:
        return FIELD_BUCKETS[field_name]
    # Unknown field: derive a bucket relative to the value's own magnitude
    # (roughly one order of magnitude below it) instead of a fixed constant,
    # so small values don't get rounded away to zero.
    magnitude = max(abs(value), 1)
    return max(1, 10 ** (math.floor(math.log10(magnitude)) - 1))


def _round_to_bucket(value: float, bucket: float) -> float:
    return round(value / bucket) * bucket


def _snap_priority(weight: float) -> float:
    return min(PRIORITY_BUCKETS, key=lambda b: abs(b - weight))


def quantize_state(state: IntentState) -> IntentState:
    """Returns a *new* IntentState with priorities and constraint values
    rounded to field-appropriate buckets. Never mutates the input."""
    q = state.copy()

    for field_name, weight in q.priorities.items():
        q.priorities[field_name] = _snap_priority(weight)

    for field_name, constraint in q.constraints.items():
        bucket = _bucket_for(field_name, constraint["value"])
        constraint["value"] = _round_to_bucket(constraint["value"], bucket)

    return q
