import { humanize, fieldLabel, regionLabel } from "../lib/format";

function AgentAskCard({ agentId, ask }) {
  const trueAsk = ask.true_ask;
  const isCoupled = trueAsk && !(trueAsk.field in (ask.constraints || {}));
  return (
    <div className="agent-ask-card">
      <div className="agent-ask-id">{humanize(agentId)}</div>
      <div className="agent-ask-trust">Trust before this round: {ask.trust_score_before?.toFixed(2)}</div>
      {trueAsk && (
        <div className="agent-ask-field">
          Really wants <strong>{fieldLabel(trueAsk.field)}</strong> {trueAsk.op} <strong>{trueAsk.value}</strong>
        </div>
      )}
      {isCoupled && (
        <div className="agent-ask-coupled-note">
          Negotiated internally through {fieldLabel(Object.keys(ask.constraints || {})[0])}, linked by a coupling
          function. See the timeline below.
        </div>
      )}
      {Object.entries(ask.constraints || {}).map(([field, c]) => (
        <div className="agent-ask-field" key={field}>
          <strong>{fieldLabel(field)}</strong> {c.op} <strong>{c.value}</strong>{" "}
          <span className="agent-ask-weight">(priority {ask.priorities?.[field]})</span>
        </div>
      ))}
    </div>
  );
}

function NegotiationSteps({ steps }) {
  return (
    <div className="steps">
      {steps.map((step, i) => {
        if (step.stage === "commit_reveal") {
          return (
            <div className="step" key={i}>
              <div className="step-title">Commit then Reveal</div>
              <div className="step-body">
                Verified: {String(step.verified)}
                <br />
                Commit A: <span className="mono">{step.commit_a.slice(0, 14)}…</span>
                <br />
                Commit B: <span className="mono">{step.commit_b.slice(0, 14)}…</span>
              </div>
            </div>
          );
        }
        if (step.stage === "layer0_layer1") {
          return (
            <div className="step" key={i}>
              <div className="step-title">Layer 0/1: Weighted Utility Scoring</div>
              <div className="step-body">
                Fully feasible: {String(step.all_feasible)}, within tolerance: {String(step.within_tolerance)}
                <br />
                Utility drop, Agent A: {step.utility_drop_a}, Agent B: {step.utility_drop_b}
              </div>
            </div>
          );
        }
        if (step.stage === "layer2") {
          return (
            <div className="step" key={i}>
              <div className="step-title">
                Layer 2: Bounded Relaxation ({step.rounds_used} of {step.effective_budget} rounds, succeeded:{" "}
                {String(step.success)})
              </div>
              <div className="step-body">
                {step.rounds_log.map((r) => (
                  <div className="round-row" key={r.round}>
                    Round {r.round}: feasible {String(r.all_feasible)}, within tolerance{" "}
                    {String(r.within_tolerance)}, drop A {r.utility_drop_a}, drop B {r.utility_drop_b}
                  </div>
                ))}
              </div>
            </div>
          );
        }
        if (step.stage === "layer3") {
          return (
            <div className="step" key={i}>
              <div className="step-title">Layer 3: Deterministic Policy Tie-Break</div>
              <div className="step-body">
                {step.mitigations.map((m, mi) => (
                  <div key={mi}>
                    {fieldLabel(m.field)}: {humanize(m.winner_agent)} wins at {m.granted_value}.{" "}
                    {humanize(m.loser_agent)} conceded from {m.loser_ask} and received a mitigation clause.
                  </div>
                ))}
              </div>
            </div>
          );
        }
        return null;
      })}
    </div>
  );
}

export default function NegotiationDetail({ entry }) {
  if (entry.audit_demo) {
    return (
      <div className="detail">
        <div className="detail-note">
          {humanize(entry.audited_agent)} committed to a hash of its intent state during negotiation. What was later
          observed did not match that commitment, so the reveal fails the hash check. This is only detectable after
          the fact, not during the negotiation itself.
        </div>
        <div className="agent-asks">
          <div className="agent-ask-card">
            <div className="agent-ask-id">Committed To</div>
            {Object.entries(entry.committed_constraints || {}).map(([field, c]) => (
              <div className="agent-ask-field" key={field}>
                <strong>{fieldLabel(field)}</strong> {c.op} <strong>{c.value}</strong>
              </div>
            ))}
          </div>
          <div className="agent-ask-card">
            <div className="agent-ask-id">Actually Observed</div>
            {Object.entries(entry.actually_observed_constraints || {}).map(([field, c]) => (
              <div className="agent-ask-field" key={field}>
                <strong>{fieldLabel(field)}</strong> {c.op} <strong>{c.value}</strong>
              </div>
            ))}
          </div>
        </div>
        <div className="detail-note">
          Consequence: trust score for this pairing resets to {entry.trust_score_after_audit}. A later, completely
          legitimate negotiation ({humanize(entry.next_negotiation_attempt?.incident?.incident_type)} in{" "}
          {regionLabel(entry.next_negotiation_attempt?.incident?.region)}) is then attempted. It gets{" "}
          {entry.next_negotiation_attempt?.blocked ? "blocked" : "allowed"} by the guardrail's trust floor before
          ever reaching re-verification. {entry.prior_verified_fabric_entries_preserved} prior verified Fabric
          entries from this agent remain untouched, so poisoning is pruned forward without wiping collective memory.
        </div>
      </div>
    );
  }

  if (entry.chaos) {
    const asks = entry.agent_asks || {};
    return (
      <div className="detail">
        <div className="agent-asks">
          {Object.entries(asks).map(([agentId, ask]) => (
            <AgentAskCard key={agentId} agentId={agentId} ask={ask} />
          ))}
        </div>
        <div className="detail-note">
          The genuine negotiation ran normally. The resolution was then tampered with before reaching the guardrail.
          The timeline below is from the genuine, pre-tamper negotiation.
        </div>
        <NegotiationSteps steps={entry.genuine_negotiation_steps || []} />
      </div>
    );
  }

  if (entry.fabric_hit) {
    return (
      <div className="detail">
        <div className="detail-note">
          This exact incident and region was already verified from a previous negotiation, so nothing needed to
          negotiate again. This is the ratchet effect: an insight discovered once was reused instantly.
        </div>
      </div>
    );
  }

  const asks = entry.result?.agent_asks || {};
  return (
    <div className="detail">
      <div className="agent-asks">
        {Object.entries(asks).map(([agentId, ask]) => (
          <AgentAskCard key={agentId} agentId={agentId} ask={ask} />
        ))}
      </div>
      <NegotiationSteps steps={entry.negotiation_steps || []} />
    </div>
  );
}
