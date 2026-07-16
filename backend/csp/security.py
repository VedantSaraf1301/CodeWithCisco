"""
Commit-then-reveal for fairness (not confidentiality): both agents publish
H(state || nonce) before either reveals its actual quantized values, so
neither side can adapt its own offer after seeing the other's.

Post-hoc audit: if an agent's revealed state doesn't hash-match its earlier
commitment, we know it lied or tampered post-commit, and its trust_score for
that pairing resets to 0.
"""
import hashlib
import json
from typing import Dict

from .intent_state import IntentState

# Sentinel written into a trust_registry when an audit catches an agent
# lying, distinct from the neutral trust_score=0.0 every fresh pairing
# starts at. Lets the guardrail tell "never negotiated with this agent yet"
# apart from "this agent was caught being dishonest" -- only the latter
# should ever block future writes.
AUDIT_FAIL_TRUST = -1.0


def _canonical(state: IntentState) -> str:
    # sort_keys makes the serialization deterministic across processes.
    return json.dumps(state.to_dict(), sort_keys=True)


def commit(state: IntentState, nonce: str) -> str:
    payload = _canonical(state) + nonce
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_reveal(committed_hash: str, revealed_state: IntentState, nonce: str) -> bool:
    return commit(revealed_state, nonce) == committed_hash


def audit(agent_id: str, committed_hash: str, revealed_state: IntentState,
          nonce: str, trust_registry: Dict[str, float]) -> bool:
    """Re-checks a past commitment against what the agent actually did.
    Returns True if honest. On mismatch, zeroes that agent's trust_score
    in trust_registry (keyed by agent_id) and returns False."""
    honest = verify_reveal(committed_hash, revealed_state, nonce)
    if not honest:
        trust_registry[agent_id] = AUDIT_FAIL_TRUST
    return honest
