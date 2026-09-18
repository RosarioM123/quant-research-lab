import React from 'react'

/** Line chart of strategy equity vs frozen SPY benchmark (SVG, no deps). */
export default function EquityChart({ strategy, benchmark }) {
  const W = 560, H = 220, PAD = 36
  const all = [...strategy.map(p => p.equity), ...benchmark.map(p => p.equity)]
  const lo = Math.min(...all), hi = Math.max(...all)
  const span = hi - lo || 1
  const x = i => PAD + (i / (strategy.length - 1)) * (W - 2 * PAD)
  const y = v => H - PAD - ((v - lo) / span) * (H - 2 * PAD)
  const path = pts => pts.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.equity).toFixed(1)}`).join(' ')

  return (
    <svg className="equity-chart" viewBox={`0 0 ${W} ${H}`} role="img"
         aria-label="Equity curve vs SPY benchmark (fixture data)">
      <line className="axis" x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} />
      <line className="axis" x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} />
      <text className="tick" x={PAD} y={PAD - 6}>${hi.toFixed(2)}</text>
      <text className="tick" x={PAD} y={H - PAD + 16}>${lo.toFixed(2)}</text>
      <path className="line-benchmark" d={path(benchmark)} />
      <path className="line-strategy" d={path(strategy)} />
      <g className="legend">
        <circle cx={W - 200} cy={14} r={4} fill="#58a6ff" />
        <text x={W - 192} y={18} fill="#e6edf3">strategy (fixture)</text>
        <circle cx={W - 70} cy={14} r={4} fill="#8b949e" />
        <text x={W - 62} y={18} fill="#e6edf3">SPY buy-and-hold (fixture)</text>
      </g>
    </svg>
  )
}
