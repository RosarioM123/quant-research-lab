import React from 'react'

export default function RiskDecisions({ decisions, summary }) {
  return (
    <div>
      <p style={{ color: '#8b949e', fontSize: 13 }}>
        Allowed <strong style={{ color: '#3fb950' }}>{summary.allowed}</strong>
        {' · '}Rejected <strong style={{ color: '#f85149' }}>{summary.rejected}</strong>
      </p>
      <table>
        <thead>
          <tr><th>Seq</th><th>Symbol</th><th>Decision</th><th>Code</th><th>Reason</th></tr>
        </thead>
        <tbody>
          {decisions.map(d => (
            <tr key={d.seq}>
              <td>{d.seq}</td>
              <td>{d.data.symbol}</td>
              <td>
                <span className={`pill ${d.data.allow ? 'allow' : 'reject'}`}>
                  {d.data.allow ? 'ALLOW' : 'REJECT'}
                </span>
              </td>
              <td>{d.data.code}</td>
              <td style={{ maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis' }}
                  title={d.data.reason}>{d.data.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
