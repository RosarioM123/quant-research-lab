import React from 'react'

export default function Positions({ data }) {
  const rows = Object.entries(data.positions).map(([symbol, qty]) => {
    const price = data.last_prices[symbol]
    return { symbol, qty, price, value: qty * price }
  })
  const invested = rows.reduce((s, r) => s + r.value, 0)
  const equity = invested + data.cash

  return (
    <div>
      <table>
        <thead>
          <tr><th>Symbol</th><th>Qty</th><th>Price</th><th>Value</th><th>% of equity</th></tr>
        </thead>
        <tbody>
          {rows.length === 0 && <tr><td colSpan={5}>No positions (all cash).</td></tr>}
          {rows.map(r => (
            <tr key={r.symbol}>
              <td>{r.symbol}</td>
              <td>{r.qty.toFixed(4)}</td>
              <td>${r.price.toFixed(2)}</td>
              <td>${r.value.toFixed(2)}</td>
              <td>{((r.value / equity) * 100).toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p style={{ color: '#8b949e', fontFamily: 'monospace', fontSize: 12 }}>
        Cash ${data.cash.toFixed(2)} · Equity ${equity.toFixed(2)} · fixture data
      </p>
    </div>
  )
}
