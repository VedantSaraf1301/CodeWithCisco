import { useState } from "react";

const WIDTH = 560;
const HEIGHT = 200;
const PAD = { top: 26, right: 16, bottom: 42, left: 16 };
const BAR_MAX_W = 28;

// Ordinal, not categorical: swapping the order would change the meaning
// (increasing negotiation effort), so this is a single-hue ramp, light to
// dark, not four unrelated identity colors.
const CATEGORIES = [
  { key: "cached", label: "Fabric Hit" },
  { key: "layer1", label: "Layer 1" },
  { key: "layer2", label: "Layer 2" },
  { key: "layer3", label: "Layer 3" },
];

export default function ResolutionPathChart({ counts }) {
  const [hoverKey, setHoverKey] = useState(null);
  const values = CATEGORIES.map((c) => counts[c.key] || 0);
  const max = Math.max(1, ...values);
  const total = values.reduce((a, b) => a + b, 0);

  const innerW = WIDTH - PAD.left - PAD.right;
  const innerH = HEIGHT - PAD.top - PAD.bottom;
  const slot = innerW / CATEGORIES.length;

  if (total === 0) {
    return <div className="chart-empty">Run a few incidents to see how they resolved.</div>;
  }

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="chart-svg" role="img" aria-label="Incidents by resolution path">
        <line
          x1={PAD.left}
          x2={WIDTH - PAD.right}
          y1={PAD.top + innerH}
          y2={PAD.top + innerH}
          className="chart-baseline"
        />
        {CATEGORIES.map((c, i) => {
          const v = counts[c.key] || 0;
          const barH = Math.max((v / max) * (innerH - 16), v > 0 ? 3 : 0);
          const cx = PAD.left + slot * i + slot / 2;
          const barW = Math.min(BAR_MAX_W, slot - 16);
          const x = cx - barW / 2;
          const y = PAD.top + innerH - barH;
          const isHover = hoverKey === c.key;
          return (
            <g
              key={c.key}
              onMouseEnter={() => setHoverKey(c.key)}
              onMouseLeave={() => setHoverKey(null)}
              tabIndex={0}
              onFocus={() => setHoverKey(c.key)}
              onBlur={() => setHoverKey(null)}
            >
              <rect x={cx - slot / 2 + 4} y={PAD.top} width={slot - 8} height={innerH} className="chart-hit-area" />
              {v > 0 && (
                <rect x={x} y={y} width={barW} height={barH} rx="4" className={`chart-bar step-${i} ${isHover ? "hovered" : ""}`} />
              )}
              <text x={cx} y={y - 8} textAnchor="middle" className="chart-bar-value">
                {v}
              </text>
              <text x={cx} y={PAD.top + innerH + 18} textAnchor="middle" className="chart-axis-label">
                {c.label}
              </text>
              {isHover && (
                <text x={cx} y={PAD.top + innerH + 30} textAnchor="middle" className="chart-bar-pct">
                  {Math.round((v / total) * 100)}% of {total}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
