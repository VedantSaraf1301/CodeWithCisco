"""
Flask API: REST endpoints + one SSE stream, wrapping the incident loop,
Accelerator, Guardrail, and Fabric for the Next.js dashboard.
"""
import json
import os
import queue
import threading

from flask import Flask, Response, jsonify, request

from config_loader import load_agents
from fabric import Fabric
from incidents import get_incident_types as list_incident_types, get_regions as list_regions, pick_random_incident, run_incident
from chaos import inject_chaos
from audit_demo import run_audit_demo
from agents import build_agents_from_request, negotiate_streaming

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "fabric.db")
fabric = Fabric(DB_PATH)
trust_registry: dict = {}

_subscribers: list = []
_subscribers_lock = threading.Lock()

# Every broadcast event is also kept here so a page refresh can repopulate
# the Incident Feed from history instead of starting blank -- the Fabric
# table already survives refreshes, the feed narrative should too.
_event_history: list = []
_HISTORY_LIMIT = 50


def _broadcast(event: dict) -> None:
    _event_history.append(event)
    del _event_history[:-_HISTORY_LIMIT]
    with _subscribers_lock:
        for q in _subscribers:
            q.put(event)


@app.after_request
def _add_cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


@app.route("/api/simulate/incident", methods=["POST", "OPTIONS"])
def simulate_incident():
    if request.method == "OPTIONS":
        return "", 204

    body = request.get_json(silent=True) or {}
    incident_type = body.get("incident_type")
    domain = body.get("domain")
    region = body.get("region") or body.get("context")

    if not incident_type or not domain:
        picked = pick_random_incident()
        incident_type, domain, region = picked["incident_type"], picked["domain"], picked["region"]
    elif not region:
        region = list_regions()[0]

    outcome = run_incident(fabric, trust_registry, incident_type, domain, region)
    _broadcast(outcome)
    return jsonify(outcome)


@app.route("/api/fabric", methods=["GET"])
def get_fabric():
    return jsonify(fabric.list_all())


@app.route("/api/incident-types", methods=["GET"])
def incident_types_route():
    return jsonify({"incident_types": list_incident_types(), "regions": list_regions()})


@app.route("/api/chaos/inject", methods=["POST", "OPTIONS"])
def chaos_inject():
    if request.method == "OPTIONS":
        return "", 204
    outcome = inject_chaos(fabric, trust_registry)
    _broadcast({"chaos": True, **outcome})
    return jsonify(outcome)


@app.route("/api/audit/inject", methods=["POST", "OPTIONS"])
def audit_inject():
    if request.method == "OPTIONS":
        return "", 204
    outcome = run_audit_demo(fabric)
    _broadcast({"audit_demo": True, **outcome})
    return jsonify(outcome)


@app.route("/api/agents", methods=["GET"])
def agents_route():
    """Selectable roster for the Simulator page -- reads
    configs/agents.json fresh on every call, so adding a new persona is a
    new config entry, not a code change."""
    return jsonify(list(load_agents().values()))


@app.route("/api/simulate/negotiation", methods=["POST", "OPTIONS"])
def simulate_negotiation():
    """Simulator page: builds two independent, caller-defined agents and
    streams the negotiation as newline-delimited JSON, one line per step,
    flushed the instant each step is computed -- a client reading this
    response is watching the negotiation happen, not replaying a finished
    result. Isolated from the Fabric/Guardrail/trust_registry on purpose;
    this is a sandbox, not part of the live incident pipeline."""
    if request.method == "OPTIONS":
        return "", 204
    body = request.get_json(silent=True) or {}
    try:
        agent_a, agent_b, negotiation_budget, tiebreak_winner = build_agents_from_request(body)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    def gen():
        for step in negotiate_streaming(agent_a, agent_b, negotiation_budget, tiebreak_winner):
            yield json.dumps(step) + "\n"

    return Response(gen(), mimetype="application/x-ndjson", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })


@app.route("/api/events/history", methods=["GET"])
def events_history():
    """Chronological (oldest-first), capped at the last 50 events -- lets
    the frontend repopulate the Incident Feed on load instead of only ever
    showing events that happened to arrive while connected."""
    return jsonify(_event_history)


@app.route("/api/events/stream")
def events_stream():
    def gen():
        q = queue.Queue()
        with _subscribers_lock:
            _subscribers.append(q)
        try:
            yield ": connected\n\n"
            while True:
                event = q.get()
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            with _subscribers_lock:
                if q in _subscribers:
                    _subscribers.remove(q)

    return Response(gen(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Access-Control-Allow-Origin": "*",
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=True, use_reloader=False)
