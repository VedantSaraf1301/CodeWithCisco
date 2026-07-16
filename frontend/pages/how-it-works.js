import Head from "next/head";
import PageHeader from "../components/PageHeader";
import Legend from "../components/Legend";
import { FAVICON } from "../lib/constants";

const HARD_QUESTIONS = [
  {
    title: "Innovation vs. Hallucination",
    body: "A claimed resolution is never trusted at face value. The guardrail independently re-runs the full negotiation pipeline before writing anything to the Fabric. If the claim can't be re-derived, it's rejected outright, never stored as \"unverified.\"",
  },
  {
    title: "Poisoning & Drift",
    body: "Every write is checked against the source pairing's trust score. An agent caught lying (a commit-reveal hash mismatch) is permanently blocked from future writes, but its past verified entries stay untouched. Poisoning is pruned forward, not by wiping the Fabric.",
  },
  {
    title: "Consistency Model: Scoped",
    body: "Every entry is keyed by (incident signature, domain scope). Two agents can reach different, equally valid answers for different regions without conflict, since they never share a key. No locking, no global consensus needed.",
  },
];

export default function HowItWorksPage() {
  return (
    <>
      <Head>
        <title>Cognition Fabric &middot; How It Works</title>
        <link rel="icon" href={FAVICON} />
      </Head>

      <PageHeader
        kicker="Documentation"
        title="How It Works"
        subtitle="The negotiation protocol, the shared memory layer, and the guardrails between them."
      />

      <div className="doc-section">
        <h2>Phase 1: Negotiation</h2>
        <p>
          Two agents with opposing goals reach a binding agreement with no human coordinator, through four layers,
          tried in order:
        </p>
        <ol className="doc-list">
          <li>
            <strong>Layer 0/1, weighted utility scoring.</strong> If the two agents' hard constraints don't directly
            conflict, the best joint value is picked immediately. Most incidents resolve here.
          </li>
          <li>
            <strong>Layer 2, bounded relaxation.</strong> If they conflict, priority weights (never hard constraints)
            relax over a capped number of rounds. A higher trust score for the pairing shrinks that cap, since
            familiar agents reconverge faster.
          </li>
          <li>
            <strong>Layer 3, deterministic tie-break.</strong> If rounds run out, an externally supplied policy
            ranking decides the winner. The losing side isn't just overridden. It receives one bounded mitigation
            clause.
          </li>
        </ol>
        <p>
          Before any of this, both agents exchange a hash commitment of their intent state and only reveal actual
          values afterward, so neither can react to the other's real position. A later audit can still catch a lie:
          if what an agent actually did doesn't match its earlier commitment, the mismatch is detectable and its
          trust score resets to zero.
        </p>
      </div>

      <div className="doc-section">
        <h2>Phase 2: Shared Memory</h2>
        <p>
          Negotiating the same conflict twice is wasted work. The Fabric is a persistent store (SQLite) of every
          verified resolution. Before negotiating, the incident loop checks the Fabric first, keyed by
          (incident signature, domain scope):
        </p>
        <ul className="doc-list">
          <li>Found: return the cached result instantly. No negotiation runs.</li>
          <li>Not found: negotiate, verify, then write. Next time, it's a cache hit.</li>
        </ul>
        <p>
          That's the ratchet effect: solve a problem once, never solve it again. The Accelerator is the glue that
          only ever writes through the Guardrail, which independently re-derives the claimed resolution, checks the
          source agents' trust floor, and checks for a scope conflict before anything is accepted.
        </p>
      </div>

      <div className="doc-section">
        <h2>Three Hard Questions</h2>
        <div className="doc-grid">
          {HARD_QUESTIONS.map((q) => (
            <div className="doc-card" key={q.title}>
              <h3>{q.title}</h3>
              <p>{q.body}</p>
            </div>
          ))}
        </div>
      </div>

      <Legend />
    </>
  );
}
