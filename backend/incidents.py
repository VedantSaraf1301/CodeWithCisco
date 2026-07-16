"""
Synthetic incident generator + the fabric-first negotiation loop that
produces the ratchet effect: check the Fabric by (incident_signature,
domain_scope) before ever negotiating; only fall back to the full Layer
0-3 pipeline on a miss.

Incident types and agent definitions are loaded from configs/*.json, not
hardcoded here -- adding a new incident type or a new agent is a new
config entry, not a code change, and takes effect immediately (config is
re-read on every call, no restart needed). Whichever two agent_ids a given
incident type's config names run through it; trust_score accumulates per
agent_id in the caller's trust_registry, so a pairing that recurs across
incidents (the common case, but not a requirement) reconverges faster over
time.

Incident numbers are seeded deterministically from (incident_type, domain,
region) rather than randomized, so repeating the *same* incident always
produces the *same* agent asks -- required for the Fabric cache hit to be
a genuine repeat, not a coincidence.
"""
import hashlib
import random
from typing import Dict, List, Tuple

from csp.intent_state import IntentState
from accelerator import accelerate
from config_loader import load_agents, load_incident_types, load_regions
from coupling import derive, project_to_control_field
from fabric import Fabric


def _seeded_int(key: str, lo: int, hi: int) -> int:
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    return lo + (int(digest, 16) % (hi - lo + 1))


def incident_signature(incident_type: str, domain: str) -> str:
    return hashlib.sha256(f"{incident_type}:{domain}".encode("utf-8")).hexdigest()[:16]


def get_incident_types() -> List[Dict]:
    return [{"type": t["type"], "domain": t["domain"]} for t in load_incident_types()]


def get_regions() -> List[str]:
    return load_regions()


def _template_for(incident_type: str) -> Dict:
    for t in load_incident_types():
        if t["type"] == incident_type:
            return t
    raise ValueError(f"unknown incident_type: {incident_type}")


def agents_for_incident_type(incident_type: str) -> Tuple[str, str]:
    """Which two agent_ids a given incident type's config actually names --
    callers that need trust_score *before* building the negotiation states
    (to seed them) shouldn't assume fixed agent names."""
    template = _template_for(incident_type)
    return template["agent_a"]["agent_id"], template["agent_b"]["agent_id"]


def _agent_profile(agent_id: str) -> Dict:
    agents = load_agents()
    return agents.get(agent_id, {"mission": "", "risk_level": "unspecified"})


def build_negotiation_states(
    incident_type: str, domain: str, region: str, trust_a: float, trust_b: float
) -> Tuple[IntentState, IntentState, str, Dict[str, Dict]]:
    template = _template_for(incident_type)
    seed_key = f"{incident_type}:{domain}:{region}"

    a_cfg, b_cfg = template["agent_a"], template["agent_b"]
    agent_a_id, agent_b_id = a_cfg["agent_id"], b_cfg["agent_id"]

    if template.get("coupled"):
        control_field, derived_field = template["control_field"], template["derived_field"]
        coupling = template["coupling"]
        a_ask_value = _seeded_int(f"{seed_key}:a", *a_cfg["range"])  # agent A's real derived-field ask
        b_value = _seeded_int(f"{seed_key}:b", *b_cfg["range"])      # agent B's real control-field ask
        # Project agent A's derived-field constraint onto the shared control
        # field so both agents negotiate over the same field name -- the
        # rest of the pipeline (Layer 0-3) is completely unaware this is a
        # cross-field coupling.
        a_constraint = project_to_control_field({"op": a_cfg["op"], "value": a_ask_value}, coupling)
        field = control_field
        a_value = a_constraint["value"]
        a_op = a_constraint["op"]
        b_op = b_cfg["op"]
        # What agent A actually asked for, in its own terms -- for display
        # only, since its real constraint (on the derived field) never
        # exists as such inside the negotiation itself.
        true_asks = {
            agent_a_id: {"field": derived_field, "op": a_cfg["op"], "value": a_ask_value},
            agent_b_id: {"field": control_field, "op": b_op, "value": b_value},
        }
    else:
        field = a_cfg["field"]
        a_value = _seeded_int(f"{seed_key}:a", *a_cfg["range"])
        b_value = _seeded_int(f"{seed_key}:b", *b_cfg["range"])
        a_op, b_op = a_cfg["op"], b_cfg["op"]
        true_asks = {
            agent_a_id: {"field": field, "op": a_op, "value": a_value},
            agent_b_id: {"field": field, "op": b_op, "value": b_value},
        }

    profile_a, profile_b = _agent_profile(agent_a_id), _agent_profile(agent_b_id)
    a_priority, b_priority = a_cfg["priority"], b_cfg["priority"]

    state_a = IntentState(
        agent_id=agent_a_id,
        domain=domain,
        policy_profile={
            "mission": profile_a.get("mission", ""),
            "risk_level": profile_a.get("risk_level", "unspecified"),
            "constraint_priority": [field] if a_priority >= b_priority else [],
        },
        priorities={field: a_priority},
        constraints={field: {"op": a_op, "value": a_value}},
        tolerance=0.3,
        negotiation_budget=5,
        trust_score=trust_a,
    )
    state_b = IntentState(
        agent_id=agent_b_id,
        domain=domain,
        policy_profile={
            "mission": profile_b.get("mission", ""),
            "risk_level": profile_b.get("risk_level", "unspecified"),
            "constraint_priority": [field] if b_priority > a_priority else [],
        },
        priorities={field: b_priority},
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
    template = _template_for(incident_type)
    if not template.get("coupled"):
        return {}
    control_field, derived_field = template["control_field"], template["derived_field"]
    if control_field not in resolution:
        return {}
    return {derived_field: derive(resolution[control_field], template["coupling"])}


def pick_random_incident() -> Dict:
    template = random.choice(load_incident_types())
    region = random.choice(load_regions())
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

    template = _template_for(incident_type)
    agent_a_id, agent_b_id = template["agent_a"]["agent_id"], template["agent_b"]["agent_id"]
    trust_a = trust_registry.get(agent_a_id, 0.0)
    trust_b = trust_registry.get(agent_b_id, 0.0)
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
