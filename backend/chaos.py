"""
Chaos Injector: runs a real negotiation, then tampers with the resolution
before it reaches the guardrail -- simulating a compromised/rogue agent
claiming a result it didn't actually derive. Proves the guardrail's
independent re-verification (not the negotiation itself) is what protects
the Fabric.
"""
import copy
import random
from typing import Dict

from csp.negotiate import negotiate
from accelerator import accelerate
from fabric import Fabric
from incidents import INCIDENT_TYPES, REGIONS, build_negotiation_states, incident_signature


def inject_chaos(fabric: Fabric, trust_registry: Dict[str, float]) -> Dict:
    template = random.choice(INCIDENT_TYPES)
    region = random.choice(REGIONS)
    incident_type, domain = template["type"], template["domain"]

    trust_a = trust_registry.get("network_ops_agent", 0.0)
    trust_b = trust_registry.get("security_agent", 0.0)
    state_a, state_b, domain_scope, true_asks = build_negotiation_states(
        incident_type, domain, region, trust_a, trust_b
    )

    genuine = negotiate(state_a, state_b)
    corrupted = copy.deepcopy(genuine)
    field = next(iter(corrupted["resolution"]))
    corrupted["resolution"][field] = corrupted["resolution"][field] + 9999  # egregious, undeniable tamper

    sig = incident_signature(incident_type, domain)
    accel = accelerate(state_a, state_b, sig, domain_scope, fabric, trust_registry, precomputed_result=corrupted)

    agent_asks = genuine["agent_asks"]
    for agent_id, true_ask in true_asks.items():
        agent_asks[agent_id]["true_ask"] = true_ask

    return {
        "blocked": accel["guardrail_status"] == "REJECTED",
        "reason": accel["reason_code"],
        "incident": {"incident_type": incident_type, "domain": domain, "region": region},
        "tampered_field": field,
        "genuine_value": genuine["resolution"][field],
        "tampered_value": corrupted["resolution"][field],
        "genuine_negotiation_steps": genuine["steps"],
        "agent_asks": agent_asks,
    }
