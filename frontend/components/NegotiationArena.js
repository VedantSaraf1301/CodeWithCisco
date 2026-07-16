import { fieldLabel, humanize } from "../lib/format";
import AgentTerminal from "./AgentTerminal";

export default function NegotiationArena({ agentAName, agentBName, field, steps, running, error }) {
  if (steps.length === 0 && !running && !error) return null;

  const last = steps[steps.length - 1];
  const resolved = last?.speaker === "system" && last?.stage === "resolved";

  return (
    <div className="arena">
      <div className="terminal-pair">
        <AgentTerminal role="a" agentName={agentAName} steps={steps} running={running} accentClass="a" />
        <AgentTerminal role="b" agentName={agentBName} steps={steps} running={running} accentClass="b" />
      </div>

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
            {last.winner ? (
              <>
                {" "}
                &middot; {humanize(last.winner)} won, {humanize(last.loser)} received a mitigation clause
              </>
            ) : (
              " · both agents accepted the outcome"
            )}
          </div>
        </div>
      )}
    </div>
  );
}
