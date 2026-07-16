// Finds this agent's current priority by scanning the live step stream for
// its most recent concession -- falls back to its starting value if it
// hasn't conceded (or the simulation hasn't started yet).
function currentPriority(agentName, steps, fallback) {
  for (let i = steps.length - 1; i >= 0; i--) {
    const s = steps[i];
    if (s.stage === "concede" && s.agent_id === agentName) {
      return s.new_priority;
    }
  }
  return fallback;
}

function concessionCount(agentName, steps) {
  return steps.filter((s) => s.stage === "concede" && s.agent_id === agentName).length;
}

export default function AgentProfileCard({ name, op, value, priority, tolerance, steps, accentClass }) {
  const live = currentPriority(name, steps, Number(priority));
  const original = Number(priority);
  const conceded = concessionCount(name, steps);
  const erosionPct = original > 0 ? Math.max(0, Math.min(100, (live / original) * 100)) : 100;

  return (
    <div className={`agent-profile-card ${accentClass}`}>
      <div className="agent-profile-name">{name || (accentClass === "a" ? "Agent A" : "Agent B")}</div>

      <div className="agent-profile-row hard">
        <span className="agent-profile-label">Hard limit &middot; never crosses this</span>
        <span className="agent-profile-value">
          {op} {value}
        </span>
      </div>

      <div className="agent-profile-row">
        <span className="agent-profile-label">
          Priority &middot; negotiable{conceded > 0 ? ` (conceded ${conceded}x)` : ""}
        </span>
        <span className="agent-profile-value">
          {live.toFixed(3)} <span className="agent-profile-muted">/ started at {original.toFixed(1)}</span>
        </span>
      </div>
      <div className="priority-bar">
        <div className="priority-bar-fill" style={{ width: `${erosionPct}%` }} />
      </div>

      <div className="agent-profile-row">
        <span className="agent-profile-label">Tolerance &middot; walk-away threshold</span>
        <span className="agent-profile-value">{Number(tolerance).toFixed(1)}</span>
      </div>
    </div>
  );
}
