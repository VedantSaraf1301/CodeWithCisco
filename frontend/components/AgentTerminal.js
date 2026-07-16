import { useEffect, useRef } from "react";

const STAGE_PREFIX = {
  profile: "init",
  layer0_check: "check",
  react: "react",
  concede: "concede",
  tiebreak_result: "result",
};

export default function AgentTerminal({ role, agentName, steps, running, accentClass }) {
  const bodyRef = useRef(null);

  // Only this agent's own lines, plus the neutral system lines both sides
  // are reacting to -- never the other agent's private reasoning, since
  // that's not something this terminal was ever shown.
  const lines = steps.filter((s) => s.speaker === role || s.speaker === "system");

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [lines.length]);

  return (
    <div className={`terminal ${accentClass}`}>
      <div className="terminal-header">
        <span className="terminal-dot red" />
        <span className="terminal-dot yellow" />
        <span className="terminal-dot green" />
        <span className="terminal-title">{agentName || (role === "a" ? "Agent A" : "Agent B")}</span>
      </div>
      <div className="terminal-body" ref={bodyRef}>
        {lines.length === 0 && !running && <div className="terminal-line dim">$ waiting for negotiation to start&hellip;</div>}
        {lines.map((s, i) => (
          <div className={`terminal-line ${s.speaker === "system" ? "system" : "self"}`} key={i}>
            <span className="terminal-prompt">
              {s.speaker === "system" ? "··" : `[${STAGE_PREFIX[s.stage] || s.stage}]`}
            </span>{" "}
            {s.detail}
          </div>
        ))}
        {running && <div className="terminal-cursor" />}
      </div>
    </div>
  );
}
