import React from 'react'

export default function LedgerTail({ records }) {
  return (
    <div className="ledger-list">
      {records.map(r => (
        <div className="row" key={r.seq}>
          <span className="seq">#{r.seq}</span>
          <span className="type">{r.type}</span>
          <span className="hash" title={r.hash}>{r.hash.slice(0, 16)}…</span>
        </div>
      ))}
    </div>
  )
}
