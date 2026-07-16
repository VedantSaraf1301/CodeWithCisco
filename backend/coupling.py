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
"""
from typing import Dict

# derived_value = intercept + slope * control_value (slope assumed positive:
# every coupling below is "more control -> more derived cost").
COUPLINGS = {
    ("inspection_level", "latency_ms"): {"intercept": 10.0, "slope": 17.5},
}


def project_to_control_field(control_field: str, derived_field: str, derived_constraint: Dict) -> Dict:
    """Rewrites a constraint expressed on the derived field (e.g.
    latency_ms <= 50) into an equivalent constraint on the control field
    (e.g. inspection_level <= 2.29), using the coupling's inverse."""
    coupling = COUPLINGS[(control_field, derived_field)]
    control_value = (derived_constraint["value"] - coupling["intercept"]) / coupling["slope"]
    return {"op": derived_constraint["op"], "value": control_value}


def derive(control_field: str, derived_field: str, control_value: float) -> float:
    """Given the negotiated control-field value, compute the resulting
    derived-field value, purely for human-readable display -- never fed
    back into negotiation, the guardrail, or the Fabric's stored resolution."""
    coupling = COUPLINGS[(control_field, derived_field)]
    return round(coupling["intercept"] + coupling["slope"] * control_value, 2)
