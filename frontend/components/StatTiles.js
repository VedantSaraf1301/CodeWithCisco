function StatTile({ label, value, accentVar, icon: IconCmp }) {
  return (
    <div className="stat-tile" style={{ "--tile-accent": `var(${accentVar})` }}>
      {IconCmp && <IconCmp className="stat-icon" />}
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

export default function StatTiles({ incidentsRun, fabricReuses, verifiedEntries, blockedWrites, icons }) {
  return (
    <div className="stats">
      <StatTile label="Incidents Run" value={incidentsRun} accentVar="--series-aqua" icon={icons.Activity} />
      <StatTile label="Fabric Reuses" value={fabricReuses} accentVar="--series-blue" icon={icons.Database} />
      <StatTile label="Verified Entries" value={verifiedEntries} accentVar="--status-good" icon={icons.Search} />
      <StatTile label="Blocked Writes" value={blockedWrites} accentVar="--status-critical" icon={icons.Zap} />
    </div>
  );
}
