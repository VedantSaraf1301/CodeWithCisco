"""
Autonomous Guardrail: the single gate a negotiated resolution must pass
before it's allowed into the Fabric. Deterministic, no ML -- every check
below is explainable line-by-line in a live defense.

Answers the three hard questions from the brief:

1. Innovation vs hallucination: a claimed resolution is never trusted at
   face value. The guardrail independently re-runs the full negotiation
   pipeline (deterministic: same states in, same resolution out) and
   rejects anything that doesn't reproduce. There is no "unverified /
   maybe" bucket -- it's VERIFIED or REJECTED.

2. Poisoning / drift: every write is checked against the source pairing's
   trust_score. An agent that a prior commit-reveal audit caught lying has
   its trust_score pinned at csp.AUDIT_FAIL_TRUST, and the guardrail refuses
   any future write from it. Already-VERIFIED past rows are untouched --
   they were independently re-derived at write time, so they don't depend
   on the agent's honesty afterward. This prunes forward without zeroing
   the whole Fabric.

3. Consistency / split-brain: scoped consistency. A write is only compared
   against the Fabric row for the exact same (incident_signature,
   domain_scope) key. An identical resolution for that key is a harmless
   re-confirmation; a *different* one is a same-scope conflict and is
   rejected rather than silently overwriting -- the existing verified entry
   always wins, so there's never a moment where two contradictory answers
   are both "current" for one scope.
"""
from typing import Dict, Tuple

from csp import negotiate, AUDIT_FAIL_TRUST
from csp.intent_state import IntentState
from fabric import Fabric

MATCH_EPSILON = 1e-6


def _resolutions_match(a: Dict[str, float], b: Dict[str, float]) -> bool:
    if set(a) != set(b):
        return False
    return all(abs(a[k] - b[k]) < MATCH_EPSILON for k in a)


def guardrail_check(
    claimed_result: Dict,
    state_a: IntentState,
    state_b: IntentState,
    fabric: Fabric,
    incident_signature: str,
    domain_scope: str,
    trust_registry: Dict[str, float],
) -> Tuple[str, str]:
    """Returns (guardrail_status, reason_code). guardrail_status is always
    "VERIFIED" or "REJECTED" -- never a soft "unverified" state."""

    # --- Check 2: trust floor ---
    for agent_id in claimed_result["agents"]:
        if trust_registry.get(agent_id, 0.0) <= AUDIT_FAIL_TRUST:
            return "REJECTED", f"TRUST_FLOOR_BREACH:{agent_id}"

    # --- Check 1: independent re-derivation (innovation vs hallucination) ---
    reverified = negotiate(state_a, state_b)
    if not _resolutions_match(reverified["resolution"], claimed_result["resolution"]):
        return "REJECTED", "UNVERIFIABLE_RESOLUTION"

    # --- Check 3: scoped-consistency conflict check ---
    existing = fabric.lookup(incident_signature, domain_scope)
    if existing is not None:
        if _resolutions_match(existing["resolution"], claimed_result["resolution"]):
            return "VERIFIED", "ALREADY_PRESENT_IDENTICAL"
        return "REJECTED", "SCOPE_CONFLICT_PRESERVES_EXISTING"

    return "VERIFIED", f"LAYER_{claimed_result['layer_used']}_REVERIFIED"
