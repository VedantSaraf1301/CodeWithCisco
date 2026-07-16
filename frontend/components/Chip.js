export default function Chip({ label, value }) {
  return (
    <span className="chip">
      <span className="chip-label">{label}</span>
      <span className="chip-value">{value}</span>
    </span>
  );
}
