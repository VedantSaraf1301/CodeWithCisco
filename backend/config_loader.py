"""
Loads agent, incident-type, and region definitions from JSON files instead
of hardcoded Python structures. Re-read from disk on every call rather than
cached at import time, so adding a new incident type or agent is a new
entry in these files -- no code change, no restart required.
"""
import json
import os
from typing import Dict, List

_CONFIG_DIR = os.path.join(os.path.dirname(__file__), "configs")


def _load(filename: str):
    path = os.path.join(_CONFIG_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_agents() -> Dict[str, Dict]:
    return {a["agent_id"]: a for a in _load("agents.json")}


def load_incident_types() -> List[Dict]:
    return _load("incident_types.json")


def load_regions() -> List[str]:
    return _load("regions.json")
