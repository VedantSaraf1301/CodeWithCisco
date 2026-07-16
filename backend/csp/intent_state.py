"""
IntentState: the negotiation schema every agent speaks.
Kept as a plain dataclass + dict conversion so it can be hashed, JSON-dumped
for commit-reveal, and stored verbatim in the Fabric.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, List


@dataclass
class IntentState:
    agent_id: str
    domain: str
    policy_profile: Dict            # {"mission": str, "risk_level": str, "constraint_priority": [str, str]}
    priorities: Dict[str, float]    # field -> weight 0.0-1.0
    constraints: Dict[str, Dict]    # field -> {"op": "<=" | ">=", "value": number}
    tolerance: float = 0.1
    negotiation_budget: int = 5
    trust_score: float = 0.0
    version: int = 1

    def to_dict(self) -> Dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict) -> "IntentState":
        return IntentState(
            agent_id=d["agent_id"],
            domain=d["domain"],
            policy_profile=d["policy_profile"],
            priorities=dict(d["priorities"]),
            constraints={k: dict(v) for k, v in d["constraints"].items()},
            tolerance=d.get("tolerance", 0.1),
            negotiation_budget=d.get("negotiation_budget", 5),
            trust_score=d.get("trust_score", 0.0),
            version=d.get("version", 1),
        )

    def copy(self) -> "IntentState":
        return IntentState.from_dict(self.to_dict())
