"""
Live demonstration of the post-hoc audit / lie-detection mechanism from the
Phase 1 submission: an agent commits to a hash of its intent state before
revealing it, but its later *actual* observed behavior turns out not to
match what it committed to. Commit-then-reveal alone can't catch this --
only a later audit against the retained hash can. This is the concrete
mechanism Phase 2's poisoning-mitigation answer depends on.

Uses its own isolated trust dict rather than the app's shared
trust_registry, so demonstrating a permanent trust reset here doesn't
permanently break the main incident flow's security_agent for the rest of
the session -- the effect (blocked future writes, untouched past writes) is
still completely real, just scoped to this demo run.
"""
import random
import secrets
from typing import Dict

from accelerator import accelerate
from csp.quantize import quantize_state
from csp.security import audit, commit
from fabric import Fabric
from incidents import agents_for_incident_type, get_incident_types, get_regions, build_negotiation_states, incident_signature


def run_audit_demo(fabric: Fabric) -> Dict:
    demo_trust: Dict[str, float] = {}

    template = random.choice(get_incident_types())
    regions = get_regions()
    region = random.choice(regions)
    incident_type, domain = template["type"], template["domain"]
    agent_a_id, agent_b_id = agents_for_incident_type(incident_type)
    state_a, state_b, _, _ = build_negotiation_states(incident_type, domain, region, 0.0, 0.0)

    # The second (B) agent in this pairing commits to its true (quantized)
    # state, exactly as in a real handshake.
    q_security = quantize_state(state_b)
    nonce = secrets.token_hex(8)
    committed_hash = commit(q_security, nonce)

    # ...but what actually gets observed later doesn't match: it claimed a
    # stricter posture than it actually enforced.
    lied_state = q_security.copy()
    for c in lied_state.constraints.values():
        c["value"] = max(0, c["value"] - 3)

    honest = audit(agent_b_id, committed_hash, lied_state, nonce, demo_trust)

    prior_verified = [
        r for r in fabric.list_all()
        if agent_b_id in r["source_agents"] and r["guardrail_status"] == "VERIFIED"
    ]

    # Prove the consequence: a completely legitimate, later negotiation from
    # this now-distrusted agent still gets rejected by the guardrail's trust
    # floor, before it ever reaches re-verification. Reuses the SAME
    # incident type (a different region) rather than picking a fresh random
    # one, so the pairing is guaranteed to include the just-audited agent --
    # a different incident type's config could name entirely different agents.
    region2 = random.choice([r for r in regions if r != region] or regions)
    state_a2, state_b2, domain_scope2, _ = build_negotiation_states(
        incident_type, domain, region2, demo_trust.get(agent_a_id, 0.0), demo_trust.get(agent_b_id, 0.0)
    )
    sig2 = incident_signature(incident_type, domain)
    blocked = accelerate(state_a2, state_b2, sig2, domain_scope2, fabric, demo_trust)

    return {
        "audited_agent": agent_b_id,
        "hash_mismatch_detected": not honest,
        "committed_constraints": q_security.constraints,
        "actually_observed_constraints": lied_state.constraints,
        "trust_score_after_audit": demo_trust.get(agent_b_id),
        "prior_verified_fabric_entries_preserved": len(prior_verified),
        "next_negotiation_attempt": {
            "incident": {"incident_type": incident_type, "domain": domain, "region": region2},
            "blocked": blocked["guardrail_status"] == "REJECTED",
            "reason": blocked["reason_code"],
        },
    }
