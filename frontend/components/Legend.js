import { Icon } from "../lib/icons";

const ITEMS = [
  {
    dot: "var(--series-blue)",
    title: "Fabric Hit",
    body: "Same incident, domain, and region seen before. Served straight from memory, zero renegotiation.",
  },
  {
    dot: "var(--series-aqua)",
    title: "Negotiated",
    body: "Fresh conflict. Runs commit-reveal, then Layer 0/1 scoring, escalating to Layer 2/3 only if needed.",
  },
  {
    dot: "var(--status-critical)",
    title: "Chaos Injection",
    body: "A tampered resolution sent toward the Fabric. The guardrail independently re-derives it and rejects the mismatch.",
  },
  {
    dot: "var(--status-warning)",
    title: "Post-Hoc Audit",
    body: "An agent's later behavior doesn't match what it committed to. Trust resets to zero; past verified entries stay.",
  },
];

export default function Legend() {
  return (
    <div className="legend">
      <h3>
        <Icon.Info />
        How to Read This Dashboard
      </h3>
      <div className="legend-grid">
        {ITEMS.map((item) => (
          <div className="legend-item" key={item.title}>
            <span className="legend-dot" style={{ background: item.dot }} />
            <div>
              <h4>{item.title}</h4>
              <p>{item.body}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
