"""
Standalone negotiating agents for the Simulator page, built independently
of the Phase 1 CSP core (csp/negotiate.py) so each agent is a real object
with its own state and decision logic, not a config dict fed into a shared
scoring function -- and so the resolution loop is a genuine Python
generator that yields each step at the moment it's computed, not a
function that returns a finished result for the frontend to replay.

What's negotiable vs. not, made explicit:
  - `value` (the hard constraint) never changes. An agent will never accept
    a resolution that crosses it -- that's not something concession can
    touch.
  - `priority` is what actually moves. It's how much weight this agent's
    satisfaction carries when a candidate value is scored, and it's what
    erodes, round by round, when this agent is the one conceding.

This intentionally skips the commit-reveal fairness step from Phase 1 --
that's about not letting an agent react to a counterpart's exact position
before committing, which isn't the question this page is answering. This
page is about showing the reasoning itself.
"""
import time
from typing import Dict, Optional, Tuple

VALID_OPS = {"<=", ">="}
DECAY = 0.7


class NegotiatingAgent:
    """An independent agent: its own ask, its own priority, its own rules
    for what it will and won't accept. No shared state with the other
    agent -- everything here is this agent's alone."""

    def __init__(self, agent_id: str, field: str, op: str, value: float,
                 priority: float, tolerance: float, trust_score: float = 0.0):
        if op not in VALID_OPS:
            raise ValueError(f"op must be one of {sorted(VALID_OPS)}")
        if not (0 <= priority <= 1):
            raise ValueError("priority must be between 0 and 1")
        if not (0 <= tolerance <= 1):
            raise ValueError("tolerance must be between 0 and 1")

        self.agent_id = agent_id
        self.field = field
        self.op = op
        self.value = float(value)          # hard limit -- never crossed, never conceded
        self.original_priority = float(priority)
        self.priority = float(priority)    # current weight -- this is what concession erodes
        self.tolerance = float(tolerance)
        self.trust_score = float(trust_score)
        self.concessions = 0

    def satisfies_own_rule(self, candidate: float) -> bool:
        """Would this agent, alone, accept this value against its own hard rule?"""
        return candidate <= self.value if self.op == "<=" else candidate >= self.value

    def fit(self, candidate: float, lo: float, hi: float) -> float:
        """Where candidate lands in [lo, hi], from this agent's own point of
        view: 1.0 at its most favorable end, 0.0 at its least favorable."""
        if hi <= lo:
            return 1.0
        if self.op == "<=":
            return (hi - candidate) / (hi - lo)
        return (candidate - lo) / (hi - lo)

    def utility(self, candidate: float, lo: float, hi: float) -> float:
        return self.priority * self.fit(candidate, lo, hi)

    def satisfaction_drop(self, candidate: float, lo: float, hi: float) -> float:
        """0 = candidate is exactly what this agent wanted. 1 = candidate is
        this agent's worst possible outcome in the range under discussion."""
        return 1.0 - self.fit(candidate, lo, hi)

    def accepts(self, candidate: float, lo: float, hi: float) -> bool:
        """This agent's own bar for calling a candidate 'good enough' --
        independent of what the other agent thinks."""
        return self.satisfaction_drop(candidate, lo, hi) <= self.tolerance

    def concede(self) -> None:
        """This agent becomes more willing to accept a worse outcome. The
        hard constraint (self.value) is untouched -- only how much this
        agent's own satisfaction weighs in scoring erodes."""
        self.priority *= DECAY
        self.concessions += 1

    def describe(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "field": self.field,
            "op": self.op,
            "value": self.value,
            "priority": round(self.priority, 4),
            "original_priority": round(self.original_priority, 4),
            "tolerance": self.tolerance,
            "trust_score": self.trust_score,
            "concessions": self.concessions,
        }


def _feasible_range(agent_a: NegotiatingAgent, agent_b: NegotiatingAgent) -> Tuple[float, float]:
    lo, hi = float("-inf"), float("inf")
    for agent in (agent_a, agent_b):
        if agent.op == "<=":
            hi = min(hi, agent.value)
        else:
            lo = max(lo, agent.value)
    return lo, hi


def _normalize(lo: float, hi: float, agent_a: NegotiatingAgent, agent_b: NegotiatingAgent) -> Tuple[float, float]:
    if lo == float("-inf"):
        lo = 0.0
    if hi == float("inf"):
        hi = max(agent_a.value, agent_b.value) * 2
    if hi <= lo:
        hi = lo + 1.0
    return lo, hi


def _best_candidate(agent_a: NegotiatingAgent, agent_b: NegotiatingAgent, lo: float, hi: float) -> float:
    # The joint-utility-maximizing point for a linear objective is always
    # at one of the two endpoints -- see csp/layers.py for the proof.
    return max((lo, hi), key=lambda v: agent_a.utility(v, lo, hi) + agent_b.utility(v, lo, hi))


def negotiate_streaming(agent_a: NegotiatingAgent, agent_b: NegotiatingAgent, negotiation_budget: int,
                         tiebreak_winner: Optional[str], step_delay: float = 0.9):
    """Generator: yields each step the instant it's computed. Nothing here
    is precomputed and replayed -- a caller iterating this generator is
    watching the negotiation happen in real time."""

    yield {"stage": "agents_ready", "agent_a": agent_a.describe(), "agent_b": agent_b.describe()}
    time.sleep(step_delay)

    a_accepts_b_ask = agent_a.satisfies_own_rule(agent_b.value)
    b_accepts_a_ask = agent_b.satisfies_own_rule(agent_a.value)
    yield {
        "stage": "layer0_check",
        "detail": f"{agent_a.agent_id} checks {agent_b.agent_id}'s ask ({agent_b.field} {agent_b.op} {agent_b.value}) "
                   f"against its own rule ({agent_a.field} {agent_a.op} {agent_a.value}); {agent_b.agent_id} does the same in reverse.",
        "agent_a_accepts_b": a_accepts_b_ask,
        "agent_b_accepts_a": b_accepts_a_ask,
    }
    time.sleep(step_delay)

    lo, hi = _feasible_range(agent_a, agent_b)
    feasible = lo <= hi

    if not feasible:
        yield {
            "stage": "layer1_infeasible",
            "detail": f"No value can be both {agent_a.field} {agent_a.op} {agent_a.value} and "
                      f"{agent_b.field} {agent_b.op} {agent_b.value} at once. This is a genuine hard conflict; "
                      f"no amount of concession can fix it, only Layer 3 can.",
        }
        time.sleep(step_delay)
    else:
        norm_lo, norm_hi = _normalize(lo, hi, agent_a, agent_b)
        candidate = _best_candidate(agent_a, agent_b, norm_lo, norm_hi)
        a_ok = agent_a.accepts(candidate, norm_lo, norm_hi)
        b_ok = agent_b.accepts(candidate, norm_lo, norm_hi)
        yield {
            "stage": "layer1_score",
            "candidate": candidate,
            "agent_a_satisfaction": round(1 - agent_a.satisfaction_drop(candidate, norm_lo, norm_hi), 3),
            "agent_b_satisfaction": round(1 - agent_b.satisfaction_drop(candidate, norm_lo, norm_hi), 3),
            "agent_a_accepts": a_ok,
            "agent_b_accepts": b_ok,
        }
        time.sleep(step_delay)

        if a_ok and b_ok:
            yield {"stage": "resolved", "layer": 1, "rounds": 0, "resolution": candidate,
                   "winner": None, "loser": None}
            return

        # Whichever agent is currently better served becomes the one that
        # concedes each round -- decaying both agents' weights identically
        # would cancel out in every ratio that matters (a weighted average
        # is invariant to uniformly rescaling its own weights), so only the
        # currently-advantaged side actually moves.
        drop_a = agent_a.satisfaction_drop(candidate, norm_lo, norm_hi)
        drop_b = agent_b.satisfaction_drop(candidate, norm_lo, norm_hi)
        conceding = agent_a if drop_a <= drop_b else agent_b

        for rnd in range(1, negotiation_budget + 1):
            conceding.concede()
            candidate = _best_candidate(agent_a, agent_b, norm_lo, norm_hi)
            a_ok = agent_a.accepts(candidate, norm_lo, norm_hi)
            b_ok = agent_b.accepts(candidate, norm_lo, norm_hi)
            yield {
                "stage": "layer2_round",
                "round": rnd,
                "of": negotiation_budget,
                "conceding_agent": conceding.agent_id,
                "conceding_agent_new_priority": round(conceding.priority, 4),
                "candidate": candidate,
                "agent_a_satisfaction": round(1 - agent_a.satisfaction_drop(candidate, norm_lo, norm_hi), 3),
                "agent_b_satisfaction": round(1 - agent_b.satisfaction_drop(candidate, norm_lo, norm_hi), 3),
                "agent_a_accepts": a_ok,
                "agent_b_accepts": b_ok,
            }
            time.sleep(step_delay)
            if a_ok and b_ok:
                yield {"stage": "resolved", "layer": 2, "rounds": rnd, "resolution": candidate,
                       "winner": None, "loser": None}
                return

    if tiebreak_winner == "a":
        winner, loser = agent_a, agent_b
    elif tiebreak_winner == "b":
        winner, loser = agent_b, agent_a
    else:
        winner, loser = (agent_a, agent_b) if agent_a.original_priority >= agent_b.original_priority else (agent_b, agent_a)

    resolution = winner.value
    yield {
        "stage": "layer3_tiebreak",
        "winner": winner.agent_id,
        "loser": loser.agent_id,
        "resolution": resolution,
        "mitigation": f"{loser.agent_id} receives one bounded, one-time exemption -- compensated, not just overridden.",
    }
    time.sleep(step_delay)
    yield {"stage": "resolved", "layer": 3, "rounds": negotiation_budget, "resolution": resolution,
           "winner": winner.agent_id, "loser": loser.agent_id}


def _to_float(value, name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number")


def build_agents_from_request(body: Dict) -> Tuple[NegotiatingAgent, NegotiatingAgent, int, Optional[str]]:
    field = str(body.get("field") or "").strip()
    if not field:
        raise ValueError("field is required")

    tolerance = _to_float(body.get("tolerance", 0.3), "tolerance")
    negotiation_budget = int(_to_float(body.get("negotiation_budget", 5), "negotiation_budget"))
    if not (1 <= negotiation_budget <= 10):
        raise ValueError("negotiation_budget must be between 1 and 10")
    trust_score = _to_float(body.get("trust_score", 0.0), "trust_score")

    def build(key: str) -> NegotiatingAgent:
        raw = body.get(key) or {}
        agent_id = str(raw.get("agent_id") or "").strip()
        if not agent_id:
            raise ValueError("Each agent needs a name")
        return NegotiatingAgent(
            agent_id=agent_id, field=field, op=raw.get("op"),
            value=_to_float(raw.get("value"), "value"),
            priority=_to_float(raw.get("priority"), "priority"),
            tolerance=tolerance, trust_score=trust_score,
        )

    agent_a = build("agent_a")
    agent_b = build("agent_b")
    if agent_a.agent_id == agent_b.agent_id:
        raise ValueError("agents must have different names")

    tiebreak_winner = body.get("tiebreak_winner")
    return agent_a, agent_b, negotiation_budget, tiebreak_winner
