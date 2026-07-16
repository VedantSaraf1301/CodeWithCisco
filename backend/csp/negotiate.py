"""
Top-level orchestrator: quantize -> commit-reveal -> Layer 0/1 -> Layer 2 ->
Layer 3, updating the pairing's trust_score as it goes.
"""
import secrets
from typing import Dict

from .intent_state import IntentState
from .quantize import quantize_state
from .security import commit, verify_reveal
from .layers import layer1_utility_scoring, layer2_bounded_relaxation, layer3_policy_tiebreak

TRUST_GAIN_ON_MUTUAL_SUCCESS = 0.1
TRUST_DECAY_ON_FORCED_TIEBREAK = 0.05


def negotiate(state_a: IntentState, state_b: IntentState) -> Dict:
    steps: list = []

    # --- Coarse-grained rounding, then commit-then-reveal ---
    qa, qb = quantize_state(state_a), quantize_state(state_b)
    nonce_a, nonce_b = secrets.token_hex(8), secrets.token_hex(8)
    commit_a, commit_b = commit(qa, nonce_a), commit(qb, nonce_b)
    reveal_ok = verify_reveal(commit_a, qa, nonce_a) and verify_reveal(commit_b, qb, nonce_b)
    steps.append({"stage": "commit_reveal", "commit_a": commit_a, "commit_b": commit_b, "verified": reveal_ok})

    # --- Layer 0 / Layer 1: direct compatibility + weighted utility scoring ---
    # Layer 0's "no conflict, commit immediately" case is exactly the subset
    # of Layer 1's result where every field is jointly feasible and both
    # sides land within their own tolerance on the first pass -- zero
    # rounds spent, so it's evaluated as one call rather than a duplicate step.
    score = layer1_utility_scoring(qa, qb)
    steps.append({"stage": "layer0_layer1", "round": 0, **{k: v for k, v in score.items() if k != "resolution"}})

    layer_used = 1
    rounds_used = 0
    mitigations: list = []
    resolution = score["resolution"]

    if not (score["all_feasible"] and score["within_tolerance"]):
        # --- Layer 2: bounded relaxation rounds ---
        max_rounds = min(qa.negotiation_budget, qb.negotiation_budget)
        l2 = layer2_bounded_relaxation(qa, qb, max_rounds)
        steps.append({"stage": "layer2", **{k: v for k, v in l2.items() if k != "score"}})
        resolution = l2["score"]["resolution"]
        rounds_used = l2["rounds_used"]

        if l2["success"]:
            layer_used = 2
        else:
            # --- Layer 3: deterministic policy tie-break ---
            l3 = layer3_policy_tiebreak(qa, qb, resolution)
            steps.append({"stage": "layer3", "mitigations": l3["mitigations"]})
            resolution = l3["resolution"]
            mitigations = l3["mitigations"]
            layer_used = 3

    # --- Trust update for this pairing ---
    if layer_used in (1, 2):
        new_trust = min(1.0, max(qa.trust_score, qb.trust_score) + TRUST_GAIN_ON_MUTUAL_SUCCESS)
    else:
        new_trust = max(0.0, max(qa.trust_score, qb.trust_score) - TRUST_DECAY_ON_FORCED_TIEBREAK)

    return {
        "agents": [qa.agent_id, qb.agent_id],
        "domain": qa.domain,
        "resolution": resolution,
        "layer_used": layer_used,
        "rounds_used": rounds_used,
        "mitigations": mitigations,
        "trust_score_after": round(new_trust, 4),
        "steps": steps,
        "commit_hashes": {qa.agent_id: commit_a, qb.agent_id: commit_b},
        "nonces": {qa.agent_id: nonce_a, qb.agent_id: nonce_b},
        # Each agent's own (quantized) ask, revealed post-commitment -- this
        # is what actually conflicted, and is what the UI needs to show the
        # negotiation instead of just its merged outcome.
        "agent_asks": {
            qa.agent_id: {"priorities": qa.priorities, "constraints": qa.constraints,
                          "trust_score_before": state_a.trust_score},
            qb.agent_id: {"priorities": qb.priorities, "constraints": qb.constraints,
                          "trust_score_before": state_b.trust_score},
        },
    }
