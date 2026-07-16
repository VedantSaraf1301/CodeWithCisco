import Link from "next/link";
import { Icon } from "../lib/icons";
import { humanize, fieldLabel, regionLabel, relativeTime, outcomeSummary } from "../lib/format";
import Chip from "./Chip";
import NegotiationDetail from "./NegotiationDetail";

function feedKey(entry, idx) {
  return `${entry.received_at || idx}-${idx}`;
}

function ResolutionRows({ resolution, derivedFields }) {
  const merged = { ...(resolution || {}), ...(derivedFields || {}) };
  const entries = Object.entries(merged);
  if (entries.length === 0) return null;
  return (
    <div className="resolution-block">
      {entries.map(([field, value]) => (
        <div className="resolution-row" key={field}>
          <span className="field">{fieldLabel(field)}</span>
          <span className="value">{typeof value === "number" ? value : String(value)}</span>
        </div>
      ))}
    </div>
  );
}

function badgeFor(entry) {
  if (entry.audit_demo) {
    return <span className="badge badge-warning">Trust Reset</span>;
  }
  if (entry.chaos) {
    return entry.blocked ? (
      <span className="badge badge-good">Chaos Blocked</span>
    ) : (
      <span className="badge badge-critical">Chaos Allowed</span>
    );
  }
  if (entry.fabric_hit) {
    return <span className="badge badge-info">Fabric Hit</span>;
  }
  const rounds = entry.result?.rounds_used ?? 0;
  return (
    <span className="badge badge-accent">
      Negotiated &middot; {rounds} Round{rounds === 1 ? "" : "s"}
    </span>
  );
}

export default function IncidentFeed({ feed: fullFeed, expanded, toggleExpanded, limit, viewAllHref, title }) {
  const feed = limit ? fullFeed.slice(0, limit) : fullFeed;
  return (
    <div className="panel">
      <div className="panel-head">
        <div className="panel-title">
          <Icon.Activity />
          <h2>{title || "Incident Feed"}</h2>
        </div>
        <div className="panel-head-right">
          <span className="panel-note">
            {fullFeed.length} event{fullFeed.length === 1 ? "" : "s"}
          </span>
          {viewAllHref && fullFeed.length > 0 && (
            <Link href={viewAllHref} className="panel-link">
              View all &rarr;
            </Link>
          )}
        </div>
      </div>

      {feed.length === 0 ? (
        <div className="empty">
          <Icon.Inbox className="empty-icon" />
          No incidents yet. Run one to see the ratchet effect.
        </div>
      ) : (
        <div className="feed">
          {feed.map((entry, idx) => {
            const id = entry._id ?? feedKey(entry, idx);
            const isOpen = expanded.has(id);
            return (
              <div className="feed-item" key={id}>
                <div className="feed-item-top">
                  <div className="feed-item-heading">
                    <div className="feed-item-title">
                      {entry.audit_demo
                        ? `Post-Hoc Audit: ${humanize(entry.audited_agent)}`
                        : entry.chaos
                        ? `Chaos Injection: ${humanize(entry.incident?.incident_type)}`
                        : humanize(entry.incident?.incident_type)}
                    </div>
                    {!entry.audit_demo && (
                      <div className="feed-item-domain">
                        {humanize(entry.incident?.domain)} &middot; {regionLabel(entry.incident?.region)} &middot;{" "}
                        <span className="feed-time">{relativeTime(entry.received_at)}</span>
                      </div>
                    )}
                  </div>
                  <div className="feed-item-badges">
                    {badgeFor(entry)}
                    {entry.audit_demo && entry.next_negotiation_attempt?.blocked && (
                      <span className="badge badge-critical">Writes Blocked</span>
                    )}
                  </div>
                </div>

                {entry.audit_demo ? (
                  <div className="chip-row">
                    <Chip label="Hash Mismatch" value={String(entry.hash_mismatch_detected)} />
                    <Chip label="Trust After" value={entry.trust_score_after_audit} />
                    <Chip label="Entries Preserved" value={entry.prior_verified_fabric_entries_preserved} />
                  </div>
                ) : entry.chaos ? (
                  <>
                    <div className="chip-row">
                      <Chip label="Reason" value={humanize(entry.reason)} />
                      <Chip label="Field" value={fieldLabel(entry.tampered_field)} />
                    </div>
                    <div className="resolution-block">
                      <div className="resolution-row">
                        <span className="field">Genuine Value</span>
                        <span className="value">{entry.genuine_value}</span>
                      </div>
                      <div className="resolution-row">
                        <span className="field">Tampered Value</span>
                        <span className="value">{entry.tampered_value}</span>
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="chip-row">
                      <Chip label="Layer" value={entry.fabric_hit ? "Cached" : entry.result?.layer_used} />
                      <Chip label="Rounds" value={entry.result?.rounds_used ?? 0} />
                      <Chip
                        label="Guardrail"
                        value={entry.result?.guardrail_status === "VERIFIED" ? "Verified" : "Rejected"}
                      />
                    </div>
                    <ResolutionRows
                      resolution={entry.result?.resolution}
                      derivedFields={entry.result?.derived_fields}
                    />
                    <div className="outcome-banner">{outcomeSummary(entry)}</div>
                  </>
                )}

                <button className="secondary toggle-btn" onClick={() => toggleExpanded(id)}>
                  {isOpen ? "Hide Details" : "Show Details"}
                </button>
                {isOpen && <NegotiationDetail entry={entry} />}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
