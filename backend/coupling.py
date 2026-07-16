"""
Cross-field coupling: some incidents pit two agents against each other over
*different* fields that are secretly linked by a real trade-off, exactly
like the Phase 1 submission's worked example (throughput agent's latency
ceiling vs security agent's inspection floor, linked by
latency_ms = 10 + 17.5 * inspection_level -- turning up inspection is what
drives latency up).

To reuse the existing single-field negotiation pipeline unchanged, a
derived-field constraint is projected onto the control field via the
coupling's inverse function before negotiation, so both agents end up
negotiating over the same field name. The projection only ever happens
outside negotiate() (in incidents.py), so the guardrail's independent
re-verification still compares against the exact same projected inputs.

The coupling coefficients (intercept, slope) are supplied by the caller,
read from each incident type's own config entry -- not hardcoded here, so
a new coupled incident type is a new config entry, not a code change.
"""
from typing import Dict


def project_to_control_field(derived_constraint: Dict, coupling: Dict) -> Dict:
    """Rewrites a constraint expressed on the derived field (e.g.
    latency_ms <= 50) into an equivalent constraint on the control field
    (e.g. inspection_level <= 2.29), using the coupling's inverse.
    coupling: {"intercept": float, "slope": float} such that
    derived_value = intercept + slope * control_value (slope > 0: more
    control always costs more on the derived field)."""
    control_value = (derived_constraint["value"] - coupling["intercept"]) / coupling["slope"]
    return {"op": derived_constraint["op"], "value": control_value}


def derive(control_value: float, coupling: Dict) -> float:
    """Given the negotiated control-field value, compute the resulting
    derived-field value, purely for human-readable display -- never fed
    back into negotiation, the guardrail, or the Fabric's stored resolution."""
    return round(coupling["intercept"] + coupling["slope"] * control_value, 2)
