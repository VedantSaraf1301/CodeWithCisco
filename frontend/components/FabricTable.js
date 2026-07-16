import { Icon } from "../lib/icons";
import { humanize, fieldLabel, trustMeterColor } from "../lib/format";

export default function FabricTable({ fabricRows }) {
  return (
    <div className="panel">
      <div className="panel-head">
        <div className="panel-title">
          <Icon.Database />
          <h2>Fabric Memory</h2>
        </div>
        <span className="panel-note">{fabricRows.length} rows</span>
      </div>

      {fabricRows.length === 0 ? (
        <div className="empty">
          <Icon.Inbox className="empty-icon" />
          Fabric is empty.
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th className="num">ID</th>
                <th>Signature</th>
                <th>Scope</th>
                <th>Resolution</th>
                <th>Agents</th>
                <th className="num">Trust</th>
                <th>Status</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {fabricRows.map((row) => {
                const trust = row.trust_score;
                const meterPct = Math.max(0, Math.min(1, trust)) * 100;
                return (
                  <tr key={row.id} className={row.guardrail_status === "REJECTED" ? "rejected" : ""}>
                    <td className="num">{row.id}</td>
                    <td>
                      <span className="mono">{row.incident_signature.slice(0, 8)}</span>
                    </td>
                    <td>{row.domain_scope}</td>
                    <td className="resolution-cell">
                      {Object.entries(row.resolution)
                        .map(([f, v]) => `${fieldLabel(f)}: ${v}`)
                        .join(", ")}
                    </td>
                    <td title={row.source_agents.join(", ")}>{row.source_agents.map(humanize).join(", ")}</td>
                    <td className="num">
                      {trust < 0 ? (
                        <span className="distrusted-pill">Distrusted</span>
                      ) : (
                        <div className="trust-cell">
                          <span className="trust-value">{trust.toFixed(2)}</span>
                          <span className="trust-meter">
                            <span
                              className="trust-meter-fill"
                              style={{ width: `${meterPct}%`, background: trustMeterColor(trust) }}
                            />
                          </span>
                        </div>
                      )}
                    </td>
                    <td>
                      {row.guardrail_status === "VERIFIED" ? (
                        <span className="badge badge-good">Verified</span>
                      ) : (
                        <span className="badge badge-critical">Rejected</span>
                      )}
                    </td>
                    <td>{humanize(row.reason_code)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
