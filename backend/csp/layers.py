"""
The four-layer resolution pipeline.

Design note on how "hard constraints" and "tolerance" interact, since it
drives every layer below: each agent's `constraints[field].value` doubles as
that field's *ask* (the operating point the agent wants), and `op` bounds the
direction it can be pushed. A field is "feasible" when the two agents'
bounds overlap (a real number satisfies both simultaneously); it is
"infeasible" only when the bounds are directly contradictory (e.g. one side
requires <=10, the other >=50). Feasible fields always have a value chosen
via weighted utility; infeasible fields cannot ever be jointly satisfied no
matter how weights are relaxed, which is exactly why Layer 2's round loop
only helps when the block is a *tolerance* shortfall (a feasible value that
still under-serves one agent's priorities) and why genuinely infeasible
fields always fall through to Layer 3.
"""
from typing import Dict, List, Optional, Tuple

from .intent_state import IntentState

DECAY_FACTOR = 0.7


def field_feasible_range(field: str, state_a: IntentState, state_b: IntentState) -> Optional[Tuple[float, float]]:
    """Raw feasible window from the two agents' hard bounds (may be
    open-ended on one side -- that's resolved separately for scoring by
    _normalized_bounds). None means the bounds directly contradict."""
    lo, hi = float("-inf"), float("inf")
    for state in (state_a, state_b):
        c = state.constraints.get(field)
        if not c:
            continue
        if c["op"] == "<=":
            hi = min(hi, c["value"])
        else:  # ">="
            lo = max(lo, c["value"])
    if lo > hi:
        return None
    return lo, hi


def _normalized_bounds(field: str, state_a: IntentState, state_b: IntentState,
                        lo: float, hi: float) -> Tuple[float, float]:
    """Fields in this domain are non-negative real quantities, so an
    open-ended floor defaults to 0. An open-ended ceiling has no natural
    default, so it falls back to twice the highest ask on record for that
    field (generous enough that it never becomes the binding constraint)."""
    if lo == float("-inf"):
        lo = 0.0
    if hi == float("inf"):
        asks = [c["value"] for st in (state_a, state_b) for f, c in st.constraints.items() if f == field]
        hi = max(asks) * 2 if asks else 10.0
    if hi <= lo:
        hi = lo + 1.0
    return lo, hi


def _fit(state: IntentState, field: str, value: float, lo: float, hi: float) -> float:
    """Where `value` lands in the negotiated [lo, hi] window, oriented by
    this agent's own preferred direction on the field ("<=" prefers low,
    ">=" prefers high). 1.0 = the most favorable end of the window for this
    agent, 0.0 = the least favorable end."""
    if hi <= lo:
        return 1.0
    op = state.constraints.get(field, {}).get("op", "<=")
    if op == "<=":
        return (hi - value) / (hi - lo)
    return (value - lo) / (hi - lo)


def layer1_utility_scoring(
    state_a: IntentState,
    state_b: IntentState,
    weights_a: Optional[Dict[str, float]] = None,
    weights_b: Optional[Dict[str, float]] = None,
) -> Dict:
    """Scores candidate values per field and picks the utility-maximizing
    one. Returns a dict with the resolution plus enough detail for the
    caller to decide whether it's good enough (all_feasible + within
    tolerance) or needs to escalate to Layer 2."""
    weights_a = weights_a if weights_a is not None else state_a.priorities
    weights_b = weights_b if weights_b is not None else state_b.priorities

    fields = sorted(set(state_a.constraints) | set(state_b.constraints))
    resolution: Dict[str, float] = {}
    bounds: Dict[str, Tuple[float, float]] = {}
    all_feasible = True

    for field in fields:
        rng = field_feasible_range(field, state_a, state_b)

        if rng is not None:
            lo, hi = _normalized_bounds(field, state_a, state_b, *rng)
            bounds[field] = (lo, hi)
            # The per-field objective is linear in value (fit is linear),
            # so the weighted-utility optimum is always at one of the two
            # endpoints of the feasible window -- never in the interior.
            best = max(
                (lo, hi),
                key=lambda v: weights_a.get(field, 0) * _fit(state_a, field, v, lo, hi)
                + weights_b.get(field, 0) * _fit(state_b, field, v, lo, hi),
            )
            resolution[field] = best
        else:
            all_feasible = False
            ideal_a = state_a.constraints.get(field, {}).get("value")
            ideal_b = state_b.constraints.get(field, {}).get("value")
            lo, hi = min(ideal_a, ideal_b), max(ideal_a, ideal_b)
            bounds[field] = (lo, hi) if hi > lo else (lo, lo + 1.0)
            # Provisional placeholder so downstream layers have something to
            # work with; whichever side currently carries more combined
            # weight on this field leads, subject to being overridden by
            # Layer 3's explicit policy tie-break.
            wa, wb = weights_a.get(field, 0), weights_b.get(field, 0)
            resolution[field] = ideal_a if wa >= wb else ideal_b

    util_a = sum(weights_a.get(f, 0) * _fit(state_a, f, resolution[f], *bounds[f]) for f in fields)
    util_b = sum(weights_b.get(f, 0) * _fit(state_b, f, resolution[f], *bounds[f]) for f in fields)
    max_a = sum(weights_a.get(f, 0) for f in fields)
    max_b = sum(weights_b.get(f, 0) for f in fields)
    drop_a = 0.0 if max_a == 0 else (max_a - util_a) / max_a
    drop_b = 0.0 if max_b == 0 else (max_b - util_b) / max_b
    within_tolerance = drop_a <= state_a.tolerance and drop_b <= state_b.tolerance

    return {
        "resolution": resolution,
        "all_feasible": all_feasible,
        "within_tolerance": within_tolerance,
        "utility_drop_a": round(drop_a, 4),
        "utility_drop_b": round(drop_b, 4),
    }


def layer2_bounded_relaxation(state_a: IntentState, state_b: IntentState, max_rounds: int) -> Dict:
    """Each round decays priority *weights* (never the hard constraint
    bounds themselves) and re-scores. A higher trust_score for this pairing
    shrinks the effective round budget, since familiar agents are assumed
    to reconverge faster.

    Only the round-0 better-served side's weights decay each round -- that
    side becomes progressively more willing to concede. Decaying BOTH
    sides by the identical factor would be a no-op: utility_drop is a
    weighted average of fit values using an agent's own weights as both
    the numerator and denominator, and a weighted average is invariant to
    uniformly rescaling its weights. Only a *relative* shift between the
    two agents' weights can ever change which candidate wins or whether
    the tolerance gate opens."""
    trust = min(state_a.trust_score, state_b.trust_score)
    effective_budget = max(1, round(max_rounds * (1 - trust)))

    wa, wb = dict(state_a.priorities), dict(state_b.priorities)
    round0 = layer1_utility_scoring(state_a, state_b, wa, wb)
    favored = "a" if round0["utility_drop_a"] <= round0["utility_drop_b"] else "b"

    rounds_log: List[Dict] = []
    last_score = None

    for rnd in range(1, effective_budget + 1):
        if favored == "a":
            wa = {k: v * DECAY_FACTOR for k, v in wa.items()}
        else:
            wb = {k: v * DECAY_FACTOR for k, v in wb.items()}
        score = layer1_utility_scoring(state_a, state_b, wa, wb)
        last_score = score
        rounds_log.append({
            "round": rnd,
            "all_feasible": score["all_feasible"],
            "within_tolerance": score["within_tolerance"],
            "utility_drop_a": score["utility_drop_a"],
            "utility_drop_b": score["utility_drop_b"],
        })
        if score["all_feasible"] and score["within_tolerance"]:
            return {"success": True, "rounds_used": rnd, "effective_budget": effective_budget,
                    "rounds_log": rounds_log, "score": score}

    return {"success": False, "rounds_used": effective_budget, "effective_budget": effective_budget,
            "rounds_log": rounds_log, "score": last_score}


_UNRANKED = float("inf")


def _priority_rank(state: IntentState, field: str) -> float:
    """Lower is higher-priority. A field absent from constraint_priority is
    always outranked by one that's explicitly listed -- using len(order) as
    the fallback breaks this the moment order is empty, since len([]) == 0
    collides with a genuine rank-0 entry on the other side."""
    order = state.policy_profile.get("constraint_priority", [])
    return order.index(field) if field in order else _UNRANKED


def layer3_policy_tiebreak(state_a: IntentState, state_b: IntentState, fallback_resolution: Dict[str, float]) -> Dict:
    """Deterministic tie-break for fields that stayed genuinely infeasible
    through Layer 2. The protocol has no built-in domain opinion, so it
    defers entirely to each agent's externally-supplied
    policy_profile.constraint_priority. The losing side isn't just
    overridden -- it gets one bounded mitigation clause recorded alongside
    the resolution."""
    final = dict(fallback_resolution)
    mitigations = []

    for field in sorted(set(state_a.constraints) | set(state_b.constraints)):
        if field_feasible_range(field, state_a, state_b) is not None:
            continue
        rank_a, rank_b = _priority_rank(state_a, field), _priority_rank(state_b, field)
        winner, loser = (state_a, state_b) if rank_a <= rank_b else (state_b, state_a)
        final[field] = winner.constraints[field]["value"]
        mitigations.append({
            "field": field,
            "winner_agent": winner.agent_id,
            "loser_agent": loser.agent_id,
            "loser_ask": loser.constraints[field]["value"],
            "granted_value": final[field],
            "mitigation": (
                f"bounded exemption granted to {loser.agent_id}: one-time deviation "
                f"logged on '{field}' for this incident only, does not set precedent"
            ),
        })

    return {"resolution": final, "mitigations": mitigations}
