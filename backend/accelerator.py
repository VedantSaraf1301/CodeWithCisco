"""
Accelerator: propagates a negotiated (or chaos-corrupted, for testing)
result through the guardrail and, if it passes, writes it into the Fabric.
This is the only path anything ever takes into fabric_memory.
"""
from typing import Dict, List, Optional

from csp.intent_state import IntentState
from csp.negotiate import negotiate
from csp.security import AUDIT_FAIL_TRUST
from fabric import Fabric
from guardrail import guardrail_check


def accelerate(
    state_a: IntentState,
    state_b: IntentState,
    incident_signature: str,
    domain_scope: str,
    fabric: Fabric,
    trust_registry: Dict[str, float],
    precomputed_result: Optional[Dict] = None,
) -> Dict:
    result = precomputed_result if precomputed_result is not None else negotiate(state_a, state_b)

    status, reason_code = guardrail_check(
        result, state_a, state_b, fabric, incident_signature, domain_scope, trust_registry
    )

    # Every attempt is logged, VERIFIED or REJECTED, so the audit trail
    # stays visible -- a chaos-blocked write should still show up in the
    # Fabric table as evidence the guardrail caught it, not disappear.
    if reason_code != "ALREADY_PRESENT_IDENTICAL":
        fabric.save(
            incident_signature=incident_signature,
            domain_scope=domain_scope,
            resolution=result["resolution"],
            source_agents=result["agents"],
            trust_score=result["trust_score_after"],
            guardrail_status=status,
            reason_code=reason_code,
        )

    # Trust is tracked per-agent here (a simplification of Phase 1's
    # per-pairing trust matrix, reasonable at prototype scale). An agent
    # already zeroed out by a prior audit stays zeroed regardless of this
    # negotiation's outcome.
    for agent_id in result["agents"]:
        if trust_registry.get(agent_id, 0.0) > AUDIT_FAIL_TRUST:
            trust_registry[agent_id] = result["trust_score_after"]

    return {"negotiation": result, "guardrail_status": status, "reason_code": reason_code}
