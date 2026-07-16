import { useRef, useState } from "react";

const WIDTH = 560;
const HEIGHT = 200;
const PAD = { top: 16, right: 20, bottom: 28, left: 34 };
const GRID = [0, 25, 50, 75, 100];

export default function RatchetTimelineChart({ data }) {
  const svgRef = useRef(null);
  const [hoverIdx, setHoverIdx] = useState(null);

  const innerW = WIDTH - PAD.left - PAD.right;
  const innerH = HEIGHT - PAD.top - PAD.bottom;
  const xFor = (i) => PAD.left + (data.length <= 1 ? innerW / 2 : (i / (data.length - 1)) * innerW);
  const yFor = (pct) => PAD.top + innerH - (pct / 100) * innerH;

  if (data.length === 0) {
    return <div className="chart-empty">Run a few incidents to see the ratchet effect trend.</div>;
  }

  const linePath = data.map((d, i) => `${i === 0 ? "M" : "L"} ${xFor(i)} ${yFor(d.pct)}`).join(" ");
  const areaPath = `${linePath} L ${xFor(data.length - 1)} ${PAD.top + innerH} L ${xFor(0)} ${PAD.top + innerH} Z`;
  const last = data[data.length - 1];
  const hovered = hoverIdx !== null ? data[hoverIdx] : null;

  const handleMove = (e) => {
    if (!svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * WIDTH;
    let nearest = 0;
    let best = Infinity;
    data.forEach((d, i) => {
      const dist = Math.abs(xFor(i) - x);
      if (dist < best) {
        best = dist;
        nearest = i;
      }
    });
    setHoverIdx(nearest);
  };

  const active = hovered || last;
  const activeIdx = hoverIdx !== null ? hoverIdx : data.length - 1;

  return (
    <div className="chart-wrap">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="chart-svg"
        onMouseMove={handleMove}
        onMouseLeave={() => setHoverIdx(null)}
        role="img"
        aria-label={`Cumulative fabric hit rate, currently ${last.pct} percent after ${last.index} incidents`}
      >
        {GRID.map((g) => (
          <g key={g}>
            <line x1={PAD.left} x2={WIDTH - PAD.right} y1={yFor(g)} y2={yFor(g)} className="chart-gridline" />
            <text x={PAD.left - 8} y={yFor(g) + 3} className="chart-axis-label" textAnchor="end">
              {g}%
            </text>
          </g>
        ))}

        <path d={areaPath} className="chart-area" />
        <path d={linePath} className="chart-line" />

        {hoverIdx !== null && (
          <line x1={xFor(hoverIdx)} x2={xFor(hoverIdx)} y1={PAD.top} y2={PAD.top + innerH} className="chart-crosshair" />
        )}

        <circle cx={xFor(activeIdx)} cy={yFor(active.pct)} r="5" className="chart-enddot" />
        {hoverIdx === null && (
          <text x={xFor(data.length - 1) - 10} y={yFor(last.pct) - 10} textAnchor="end" className="chart-endlabel">
            {last.pct}%
          </text>
        )}
      </svg>

      {hovered && (
        <div
          className="chart-tooltip"
          style={{ left: `${(xFor(hoverIdx) / WIDTH) * 100}%`, top: `${(yFor(hovered.pct) / HEIGHT) * 100}%` }}
        >
          <div className="chart-tooltip-value">{hovered.pct}% cached</div>
          <div className="chart-tooltip-label">after incident #{hovered.index}</div>
        </div>
      )}
    </div>
  );
}
