import { fieldLabel, humanize } from "../lib/format";

const STEP_ACCENT = {
  agents_ready: "var(--text-muted)",
  layer0_check: "var(--series-blue)",
  layer1_score: "var(--series-aqua)",
  layer1_infeasible: "var(--series-aqua)",
  layer2_round: "var(--status-warning)",
  layer3_tiebreak: "var(--status-serious)",
};

function stepTitle(step) {
  switch (step.stage) {
    case "agents_ready":
      return "Agents Created";
    case "layer0_check":
      return "Layer 0: Independent Compatibility Check";
    case "layer1_score":
      return "Layer 1: Weighted Utility Scoring";
    case "layer1_infeasible":
      return "Layer 1: Hard Conflict Detected";
    case "layer2_round":
      return `Layer 2: Concession Round ${step.round} of ${step.of}`;
    case "layer3_tiebreak":
      return "Layer 3: Deterministic Policy Tie-Break";
    default:
      return step.stage;
  }
}

function StepBody({ step }) {
  if (step.stage === "agents_ready") {
    return <div className="step-body">Both agents are set up with their own asks. Negotiation begins.</div>;
  }
  if (step.stage === "layer0_check") {
    return (
      <div className="step-body">
        {step.detail}
        <br />
        Accepts the other's raw ask: agent A {String(step.agent_a_accepts_b)}, agent B {String(step.agent_b_accepts_a)}
      </div>
    );
  }
  if (step.stage === "layer1_score") {
    return (
      <div className="step-body">
        A shared value exists that could satisfy both hard limits. Testing candidate <strong>{step.candidate}</strong>
        .
        <br />
        Agent A satisfaction: {step.agent_a_satisfaction} (accepts: {String(step.agent_a_accepts)}) &middot; Agent B
        satisfaction: {step.agent_b_satisfaction} (accepts: {String(step.agent_b_accepts)})
      </div>
    );
  }
  if (step.stage === "layer1_infeasible") {
    return <div className="step-body">{step.detail}</div>;
  }
  if (step.stage === "layer2_round") {
    return (
      <div className="step-body">
        {humanize(step.conceding_agent)} is currently better served, so it concedes: its priority weight drops to{" "}
        {step.conceding_agent_new_priority}.
        <br />
        Re-scored candidate: <strong>{step.candidate}</strong> &middot; Agent A accepts:{" "}
        {String(step.agent_a_accepts)} &middot; Agent B accepts: {String(step.agent_b_accepts)}
      </div>
    );
  }
  if (step.stage === "layer3_tiebreak") {
    return (
      <div className="step-body">
        The round budget ran out with no value both sides could tolerate. {humanize(step.winner)} wins by policy
        ranking at <strong>{step.resolution}</strong>. {step.mitigation}
      </div>
    );
  }
  return null;
}

export default function NegotiationArena({ agentAName, agentBName, field, steps, running, error }) {
  if (steps.length === 0 && !running && !error) return null;

  const last = steps[steps.length - 1];
  const resolved = last?.stage === "resolved";

  return (
    <div className="arena">
      <div className="arena-agents">
        <div className="arena-agent">
          <div className="arena-agent-avatar a">{(agentAName || "A")[0].toUpperCase()}</div>
          <div className="arena-agent-name">{agentAName || "Agent A"}</div>
        </div>
        <div className="arena-vs">
          {running && !resolved ? <span className="arena-thinking">negotiating&hellip;</span> : "vs"}
        </div>
        <div className="arena-agent">
          <div className="arena-agent-avatar b">{(agentBName || "B")[0].toUpperCase()}</div>
          <div className="arena-agent-name">{agentBName || "Agent B"}</div>
        </div>
      </div>

      <div className="steps arena-steps">
        {steps
          .filter((s) => s.stage !== "resolved")
          .map((step, i) => (
            <div className="step" style={{ "--step-accent": STEP_ACCENT[step.stage] }} key={i}>
              <div className="step-title">{stepTitle(step)}</div>
              <StepBody step={step} />
            </div>
          ))}

        {resolved && (
          <div className="resolution-card">
            <div className="resolution-card-label">Final Resolution</div>
            <div className="resolution-card-values">
              <div className="resolution-card-row">
                <span>{fieldLabel(field)}</span>
                <strong>{last.resolution}</strong>
              </div>
            </div>
            <div className="resolution-card-meta">
              Resolved at Layer {last.layer} in {last.rounds} round{last.rounds === 1 ? "" : "s"}
              {last.winner && (
                <>
                  {" "}
                  &middot; {humanize(last.winner)} won, {humanize(last.loser)} received a mitigation clause
                </>
              )}
              {!last.winner && " · both agents accepted the outcome"}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
