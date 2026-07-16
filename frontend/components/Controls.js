import { Icon } from "../lib/icons";
import { humanize, regionLabel } from "../lib/format";

export default function Controls({
  incidentTypes,
  regions,
  selectedType,
  setSelectedType,
  selectedRegion,
  setSelectedRegion,
  lastIncident,
  busy,
  onRun,
  onRepeat,
  onChaos,
  onAudit,
}) {
  return (
    <div className="controls">
      <div className="control-group">
        <span className="control-group-label">Incident</span>
        <div className="control-row">
          <select value={selectedType} onChange={(e) => setSelectedType(e.target.value)}>
            <option value="">Random type</option>
            {incidentTypes.map((t) => (
              <option key={t.type} value={t.type}>
                {humanize(t.type)} ({humanize(t.domain)})
              </option>
            ))}
          </select>
          <select value={selectedRegion} onChange={(e) => setSelectedRegion(e.target.value)}>
            <option value="">Random region</option>
            {regions.map((r) => (
              <option key={r} value={r}>
                {regionLabel(r)}
              </option>
            ))}
          </select>
          <button className="primary" onClick={onRun} disabled={busy}>
            <Icon.Play />
            Run New Incident
          </button>
          <button className="secondary" onClick={onRepeat} disabled={busy || !lastIncident}>
            <Icon.Repeat />
            Repeat Last{lastIncident ? ` (${humanize(lastIncident.incident_type)})` : ""}
          </button>
        </div>
      </div>

      <div className="control-group">
        <span className="control-group-label">Resilience Tests</span>
        <div className="control-row">
          <button className="outline-warning" onClick={onChaos} disabled={busy}>
            <Icon.Zap />
            Inject Chaos
          </button>
          <button className="outline-critical" onClick={onAudit} disabled={busy}>
            <Icon.Search />
            Simulate Dishonest Agent
          </button>
        </div>
      </div>
    </div>
  );
}
