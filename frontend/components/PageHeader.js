export default function PageHeader({ kicker, title, subtitle }) {
  return (
    <div className="page-header">
      {kicker && <div className="kicker">{kicker}</div>}
      <h1>{title}</h1>
      {subtitle && <div className="subtitle">{subtitle}</div>}
    </div>
  );
}
