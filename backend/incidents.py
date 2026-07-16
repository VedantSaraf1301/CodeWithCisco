"""
Synthetic incident generator + the fabric-first negotiation loop that
produces the ratchet effect: check the Fabric by (incident_signature,
domain_scope) before ever negotiating; only fall back to the full Layer
0-3 pipeline on a miss.

Two fixed agents run through every incident (network_ops_agent vs
security_agent) so trust_score for that pairing accumulates realistically
across the demo, visibly shrinking Layer 2's round budget over time.

Incident numbers are seeded deterministically from (incident_type, domain,
region) rather than randomized, so repeating the *same* incident always
produces the *same* agent asks -- required for the Fabric cache hit to be
a genuine repeat, not a coincidence.
"""
import hashlib
import random
from typing import Dict, List, Optional, Tuple

from csp.intent_state import IntentState
from accelerator import accelerate
from coupling import derive, project_to_control_field
from fabric import Fabric

AGENT_A_ID = "network_ops_agent"
AGENT_B_ID = "security_agent"

INCIDENT_TYPES = [
    {"type": "high_latency_flow", "domain": "cloud-infra"},
    {"type": "unauthorized_access_attempt", "domain": "zero-trust"},
    {"type": "policy_drift_detected", "domain": "zero-trust"},
    {"type": "bandwidth_saturation", "domain": "cloud-infra"},
]

REGIONS = ["us-east", "us-west", "eu-west"]


def _seeded_int(key: str, lo: int, hi: int) -> int:
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    return lo + (int(digest, 16) % (hi - lo + 1))


def incident_signature(incident_type: str, domain: str) -> str:
    return hashlib.sha256(f"{incident_type}:{domain}".encode("utf-8")).hexdigest()[:16]


# Each template says, per incident type, which field is contested, which
# direction each agent wants it pushed, and the seeded range each agent's
# ask is drawn from.
#
# high_latency_flow is a direct re-run of the Phase 1 submission's worked
# example: network_ops actually cares about latency_ms (a derived field),
# security actually cares about inspection_level (the control field), and
# the two are linked by latency_ms = 10 + 17.5 * inspection_level -- more
# inspection genuinely costs more latency, which is what makes this a real
# impasse instead of two agents independently wanting the same thing.
_TEMPLATES = {
    "high_latency_flow": {
        "coupled": True,
        "control_field": "inspection_level",
        "derived_field": "latency_ms",
        "a_field": "latency_ms", "a_op": "<=", "a_range": (45, 55), "a_priority": 0.8,
        "b_field": "inspection_level", "b_op": ">=", "b_range": (3, 5), "b_priority": 0.9,
    },
    "bandwidth_saturation": {
        "field": "bandwidth_mbps",
        "a_op": ">=", "a_range": (400, 800), "a_priority": 0.7,
        "b_op": "<=", "b_range": (150, 400), "b_priority": 0.6,
    },
    "unauthorized_access_attempt": {
        "field": "access_level",
        "a_op": ">=", "a_range": (4, 7), "a_priority": 0.5,
        "b_op": "<=", "b_range": (1, 3), "b_priority": 0.9,
    },
    "policy_drift_detected": {
        "field": "inspection_level",
        "a_op": "<=", "a_range": (1, 3), "a_priority": 0.4,
        "b_op": ">=", "b_range": (4, 8), "b_priority": 0.9,
    },
}


def build_negotiation_states(
    incident_type: str, domain: str, region: str, trust_a: float, trust_b: float
) -> Tuple[IntentState, IntentState, str, Dict[str, Dict]]:
    template = _TEMPLATES[incident_type]
    seed_key = f"{incident_type}:{domain}:{region}"

    if template.get("coupled"):
        control_field, derived_field = template["control_field"], template["derived_field"]
        a_ask_value = _seeded_int(f"{seed_key}:a", *template["a_range"])  # network_ops' real latency_ms ask
        b_value = _seeded_int(f"{seed_key}:b", *template["b_range"])      # security's real inspection_level ask
        # Project network_ops' latency constraint onto the shared control
        # field so both agents negotiate over the same field name -- the
        # rest of the pipeline (Layer 0-3) is completely unaware this is a
        # cross-field coupling.
        a_constraint = project_to_control_field(
            control_field, derived_field, {"op": template["a_op"], "value": a_ask_value}
        )
        field = control_field
        a_value = a_constraint["value"]
        a_op = a_constraint["op"]
        b_op = template["b_op"]
        # What network_ops actually asked for, in its own terms -- for
        # display only, since its real constraint (on latency_ms) never
        # exists as such inside the negotiation itself.
        true_asks = {
            AGENT_A_ID: {"field": derived_field, "op": template["a_op"], "value": a_ask_value},
            AGENT_B_ID: {"field": control_field, "op": b_op, "value": b_value},
        }
    else:
        field = template["field"]
        a_value = _seeded_int(f"{seed_key}:a", *template["a_range"])
        b_value = _seeded_int(f"{seed_key}:b", *template["b_range"])
        a_op, b_op = template["a_op"], template["b_op"]
        true_asks = {
            AGENT_A_ID: {"field": field, "op": a_op, "value": a_value},
            AGENT_B_ID: {"field": field, "op": b_op, "value": b_value},
        }

    state_a = IntentState(
        agent_id=AGENT_A_ID,
        domain=domain,
        policy_profile={
            "mission": "keep enterprise traffic flowing",
            "risk_level": "low",
            "constraint_priority": [field] if template["a_priority"] >= template["b_priority"] else [],
        },
        priorities={field: template["a_priority"]},
        constraints={field: {"op": a_op, "value": a_value}},
        tolerance=0.3,
        negotiation_budget=5,
        trust_score=trust_a,
    )
    state_b = IntentState(
        agent_id=AGENT_B_ID,
        domain=domain,
        policy_profile={
            "mission": "enforce zero-trust security posture",
            "risk_level": "high",
            "constraint_priority": [field] if template["b_priority"] > template["a_priority"] else [],
        },
        priorities={field: template["b_priority"]},
        constraints={field: {"op": b_op, "value": b_value}},
        tolerance=0.3,
        negotiation_budget=5,
        trust_score=trust_b,
    )
    domain_scope = f"{domain}:{region}"
    return state_a, state_b, domain_scope, true_asks


def derived_display_fields(incident_type: str, resolution: Dict[str, float]) -> Dict[str, float]:
    """For coupled incidents, translate the negotiated control-field value
    back into the human-readable derived field (e.g. inspection_level -> the
    resulting latency_ms), purely for display. Never fed back into
    negotiation, the guardrail, or what's stored in the Fabric."""
    template = _TEMPLATES.get(incident_type, {})
    if not template.get("coupled"):
        return {}
    control_field, derived_field = template["control_field"], template["derived_field"]
    if control_field not in resolution:
        return {}
    return {derived_field: derive(control_field, derived_field, resolution[control_field])}


def pick_random_incident() -> Dict:
    template = random.choice(INCIDENT_TYPES)
    region = random.choice(REGIONS)
    return {"incident_type": template["type"], "domain": template["domain"], "region": region}


def run_incident(fabric: Fabric, trust_registry: Dict[str, float], incident_type: str,
                  domain: str, region: str) -> Dict:
    """The fabric-first loop: this single function is the entire proof of
    the ratchet effect. Same incident twice -> full negotiation once, an
    instant cache hit the second time."""
    sig = incident_signature(incident_type, domain)
    scope = f"{domain}:{region}"

    cached = fabric.lookup(sig, scope)
    if cached is not None:
        cached = {**cached, "derived_fields": derived_display_fields(incident_type, cached["resolution"])}
        return {
            "incident": {"incident_type": incident_type, "domain": domain, "region": region},
            "fabric_hit": True,
            "negotiation_steps": [],
            "result": cached,
        }

    trust_a = trust_registry.get(AGENT_A_ID, 0.0)
    trust_b = trust_registry.get(AGENT_B_ID, 0.0)
    state_a, state_b, domain_scope, true_asks = build_negotiation_states(
        incident_type, domain, region, trust_a, trust_b
    )

    accel = accelerate(state_a, state_b, sig, domain_scope, fabric, trust_registry)

    agent_asks = accel["negotiation"]["agent_asks"]
    for agent_id, true_ask in true_asks.items():
        agent_asks[agent_id]["true_ask"] = true_ask

    return {
        "incident": {"incident_type": incident_type, "domain": domain, "region": region},
        "fabric_hit": False,
        "negotiation_steps": accel["negotiation"]["steps"],
        "result": {
            "resolution": accel["negotiation"]["resolution"],
            "layer_used": accel["negotiation"]["layer_used"],
            "rounds_used": accel["negotiation"]["rounds_used"],
            "mitigations": accel["negotiation"]["mitigations"],
            "trust_score_after": accel["negotiation"]["trust_score_after"],
            "guardrail_status": accel["guardrail_status"],
            "reason_code": accel["reason_code"],
            "agent_asks": agent_asks,
            "derived_fields": derived_display_fields(incident_type, accel["negotiation"]["resolution"]),
        },
    }
