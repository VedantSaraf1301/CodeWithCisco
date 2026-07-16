import Head from "next/head";
import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import NegotiationArena from "../components/NegotiationArena";
import AgentProfileCard from "../components/AgentProfileCard";
import { FAVICON, API_BASE } from "../lib/constants";

const FIELD_SUGGESTIONS = ["inspection_level", "latency_ms", "bandwidth_mbps", "access_level"];

const DEFAULTS = {
  field: "inspection_level",
  agentA: {
    personaId: "network_ops_agent", name: "Network Ops Agent",
    op: "<=", value: 2, priority: 0.5, tolerance: 0.3, trustScore: 0,
  },
  agentB: {
    personaId: "security_agent", name: "Security Agent",
    op: ">=", value: 6, priority: 0.9, tolerance: 0.3, trustScore: 0,
  },
  negotiationBudget: 5,
  tiebreakWinner: "b",
};

function AgentForm({ label, agent, onChange, accentClass, roster }) {
  const applyPersona = (agentId) => {
    const persona = roster.find((p) => p.agent_id === agentId);
    if (!persona) {
      onChange({ ...agent, personaId: "" });
      return;
    }
    onChange({
      ...agent,
      personaId: agentId,
      name: persona.display_name,
      op: persona.suggested_op || agent.op,
      priority: persona.suggested_priority ?? agent.priority,
    });
  };

  return (
    <div className={`agent-form ${accentClass}`}>
      <div className="agent-form-label">{label}</div>

      <label className="form-field">
        <span>Pick an agent</span>
        <select value={agent.personaId || ""} onChange={(e) => applyPersona(e.target.value)}>
          <option value="">Custom&hellip;</option>
          {roster.map((p) => (
            <option value={p.agent_id} key={p.agent_id}>
              {p.display_name}
            </option>
          ))}
        </select>
      </label>

      <label className="form-field">
        <span>Name</span>
        <input
          type="text"
          value={agent.name}
          onChange={(e) => onChange({ ...agent, name: e.target.value, personaId: "" })}
          placeholder="e.g. Throughput Agent"
        />
      </label>

      <div className="form-row">
        <label className="form-field">
          <span>Wants field</span>
          <select value={agent.op} onChange={(e) => onChange({ ...agent, op: e.target.value })}>
            <option value="<=">&le; (at most)</option>
            <option value=">=">&ge; (at least)</option>
          </select>
        </label>
        <label className="form-field">
          <span>Value</span>
          <input type="number" value={agent.value} onChange={(e) => onChange({ ...agent, value: e.target.value })} />
        </label>
      </div>

      <label className="form-field">
        <span>How much it cares: {Number(agent.priority).toFixed(1)}</span>
        <input
          type="range"
          min="0"
          max="1"
          step="0.1"
          value={agent.priority}
          onChange={(e) => onChange({ ...agent, priority: e.target.value })}
        />
      </label>

      <div className="form-row">
        <label className="form-field">
          <span>Tolerance: {Number(agent.tolerance).toFixed(1)}</span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={agent.tolerance}
            onChange={(e) => onChange({ ...agent, tolerance: e.target.value })}
          />
        </label>
        <label className="form-field">
          <span>Trust score: {Number(agent.trustScore).toFixed(1)}</span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={agent.trustScore}
            onChange={(e) => onChange({ ...agent, trustScore: e.target.value })}
          />
        </label>
      </div>
    </div>
  );
}

export default function SimulatorPage() {
  const [roster, setRoster] = useState([]);
  const [field, setField] = useState(DEFAULTS.field);
  const [agentA, setAgentA] = useState(DEFAULTS.agentA);
  const [agentB, setAgentB] = useState(DEFAULTS.agentB);
  const [negotiationBudget, setNegotiationBudget] = useState(DEFAULTS.negotiationBudget);
  const [tiebreakWinner, setTiebreakWinner] = useState(DEFAULTS.tiebreakWinner);

  const [running, setRunning] = useState(false);
  const [steps, setSteps] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/agents`)
      .then((r) => r.json())
      .then(setRoster)
      .catch(() => {});
  }, []);

  const runNegotiation = async () => {
    setError(null);
    setSteps([]);
    setRunning(true);
    try {
      const res = await fetch(`${API_BASE}/api/simulate/negotiation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          field,
          agent_a: {
            agent_id: agentA.name,
            op: agentA.op,
            value: Number(agentA.value),
            priority: Number(agentA.priority),
            tolerance: Number(agentA.tolerance),
            trust_score: Number(agentA.trustScore),
          },
          agent_b: {
            agent_id: agentB.name,
            op: agentB.op,
            value: Number(agentB.value),
            priority: Number(agentB.priority),
            tolerance: Number(agentB.tolerance),
            trust_score: Number(agentB.trustScore),
          },
          negotiation_budget: Number(negotiationBudget),
          tiebreak_winner: tiebreakWinner === "none" ? null : tiebreakWinner,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.error || "The simulator rejected this scenario.");
        setRunning(false);
        return;
      }

      // Real streaming consumption: each chunk is read off the network the
      // instant the server flushes it, not pre-fetched and replayed.
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();
        for (const line of lines) {
          if (!line.trim()) continue;
          const step = JSON.parse(line);
          setSteps((prev) => [...prev, step]);
        }
      }
    } catch {
      setError("Couldn't reach the backend. Is the Flask server running?");
    } finally {
      setRunning(false);
    }
  };

  return (
    <>
      <Head>
        <title>Cognition Fabric · Simulator</title>
        <link rel="icon" href={FAVICON} />
      </Head>

      <PageHeader
        kicker="Sandbox"
        title="Negotiation Simulator"
        subtitle="Pick two agents (or make your own) and a field they both want to control. Every step below is streamed the instant it's computed, not replayed from a finished result."
      />

      <div className="sim-layout">
        <div className="sim-form-panel">
          <label className="form-field">
            <span>Field they're both negotiating over</span>
            <input type="text" value={field} onChange={(e) => setField(e.target.value)} />
          </label>
          <div className="field-chip-row">
            {FIELD_SUGGESTIONS.map((f) => (
              <button
                type="button"
                key={f}
                className={`field-chip ${field === f ? "active" : ""}`}
                onClick={() => setField(f)}
              >
                {f}
              </button>
            ))}
          </div>

          <div className="agent-forms">
            <AgentForm label="Agent A" agent={agentA} onChange={setAgentA} accentClass="a" roster={roster} />
            <AgentForm label="Agent B" agent={agentB} onChange={setAgentB} accentClass="b" roster={roster} />
          </div>

          <div className="sim-settings">
            <label className="form-field">
              <span>Negotiation budget: {negotiationBudget} rounds</span>
              <input
                type="range"
                min="1"
                max="10"
                step="1"
                value={negotiationBudget}
                onChange={(e) => setNegotiationBudget(e.target.value)}
              />
            </label>
            <label className="form-field">
              <span>If it reaches a tie-break</span>
              <select value={tiebreakWinner} onChange={(e) => setTiebreakWinner(e.target.value)}>
                <option value="a">Agent A should win</option>
                <option value="b">Agent B should win</option>
                <option value="none">No preference (unranked)</option>
              </select>
            </label>
          </div>

          <button className="primary sim-run-btn" onClick={runNegotiation} disabled={running}>
            {running ? "Negotiating…" : "Run Negotiation"}
          </button>
          {error && <div className="sim-error">{error}</div>}
        </div>

        <div className="sim-right">
          <div className="agent-profiles">
            <AgentProfileCard
              name={agentA.name}
              op={agentA.op}
              value={agentA.value}
              priority={agentA.priority}
              tolerance={agentA.tolerance}
              steps={steps}
              accentClass="a"
            />
            <AgentProfileCard
              name={agentB.name}
              op={agentB.op}
              value={agentB.value}
              priority={agentB.priority}
              tolerance={agentB.tolerance}
              steps={steps}
              accentClass="b"
            />
          </div>

          <div className="sim-arena-panel">
            {steps.length === 0 && !running && !error && (
              <div className="empty">Configure both agents and run the negotiation to watch it unfold.</div>
            )}
            <NegotiationArena
              agentAName={agentA.name}
              agentBName={agentB.name}
              field={field}
              steps={steps}
              running={running}
              error={error}
            />
          </div>
        </div>
      </div>
    </>
  );
}
