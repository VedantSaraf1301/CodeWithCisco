const REGION_LABELS = { "us-east": "US East", "us-west": "US West", "eu-west": "EU West" };

const FIELD_LABELS = {
  latency_ms: "Latency (ms)",
  bandwidth_mbps: "Bandwidth (Mbps)",
  inspection_level: "Inspection Level",
  access_level: "Access Level",
};

export function humanize(str) {
  if (!str) return "";
  return str
    .replace(/[_\-:]/g, " ")
    .split(" ")
    .filter(Boolean)
    .map((w) => w[0].toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");
}

export function fieldLabel(field) {
  return FIELD_LABELS[field] || humanize(field);
}

export function regionLabel(region) {
  return REGION_LABELS[region] || humanize(region);
}

export function relativeTime(ts) {
  if (!ts) return "";
  const secs = Math.max(0, Math.floor((Date.now() - ts) / 1000));
  if (secs < 1) return "now";
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  return `${Math.floor(mins / 60)}h ago`;
}

export function outcomeSummary(entry) {
  if (entry.fabric_hit) {
    return "Reused instantly from Fabric memory. No negotiation was needed.";
  }
  const r = entry.result;
  if (!r) return "";
  if (r.mitigations && r.mitigations.length > 0) {
    const m = r.mitigations[0];
    return `${humanize(m.winner_agent)} won on ${fieldLabel(m.field)} at ${m.granted_value}. ${humanize(
      m.loser_agent
    )} conceded from ${m.loser_ask} and received a mitigation clause.`;
  }
  if (r.layer_used === 1) {
    return "Both agents' asks were compatible. Settled instantly with no conflict.";
  }
  return "Resolved through bounded relaxation. No tie-break was needed.";
}

export function trustMeterColor(trust) {
  if (trust < 0) return "var(--status-critical)";
  if (trust < 0.3) return "var(--status-warning)";
  return "var(--status-good)";
}
