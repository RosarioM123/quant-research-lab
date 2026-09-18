import React from 'react'
import EquityChart from './components/EquityChart.jsx'
import Positions from './components/Positions.jsx'
import LedgerTail from './components/LedgerTail.jsx'
import RiskDecisions from './components/RiskDecisions.jsx'
import meta from './fixtures/meta.json'
import equity from './fixtures/equity.json'
import positions from './fixtures/positions.json'
import ledgerTail from './fixtures/ledger_tail.json'
import riskDecisions from './fixtures/risk_decisions.json'
import './styles/main.scss'

export default function App() {
  const last = equity.strategy[equity.strategy.length - 1]
  const first = equity.strategy[0]
  const retPct = ((last.equity / first.equity - 1) * 100).toFixed(2)
  const benchLast = equity.benchmark_spy[equity.benchmark_spy.length - 1]
  const benchFirst = equity.benchmark_spy[0]
  const benchPct = ((benchLast.equity / benchFirst.equity - 1) * 100).toFixed(2)

  return (
    <div className="app">
      <header className="header">
        <h1>SIGNAL — Experiment Dashboard</h1>
        <div className="subtitle">
          $100 paper experiment · long-only · no leverage · 30 calendar days
        </div>
      </header>

      <div className="fixture-banner">
        <strong>Fixture data.</strong> {meta.note}{' '}
        The real experiment has not been run; nothing here is real trading or
        real performance.
      </div>

      <div className="stat-row">
        <div className={`stat ${retPct >= 0 ? 'pos' : 'neg'}`}>
          <div className="label">Strategy (fixture)</div>
          <div className="value">{retPct}%</div>
        </div>
        <div className={`stat ${benchPct >= 0 ? 'pos' : 'neg'}`}>
          <div className="label">SPY buy-and-hold (fixture)</div>
          <div className="value">{benchPct}%</div>
        </div>
        <div className="stat">
          <div className="label">Risk decisions</div>
          <div className="value">
            {riskDecisions.summary.allowed}A / {riskDecisions.summary.rejected}R
          </div>
        </div>
      </div>

      <div className="grid">
        <section className="panel" style={{ gridColumn: '1 / -1' }}>
          <h2>Equity curve (fixture)</h2>
          <EquityChart strategy={equity.strategy} benchmark={equity.benchmark_spy} />
        </section>
        <section className="panel">
          <h2>Positions (fixture)</h2>
          <Positions data={positions} />
        </section>
        <section className="panel">
          <h2>Risk decisions (fixture)</h2>
          <RiskDecisions decisions={riskDecisions.decisions}
                         summary={riskDecisions.summary} />
        </section>
        <section className="panel" style={{ gridColumn: '1 / -1' }}>
          <h2>Ledger tail — hash-chained (fixture)</h2>
          <LedgerTail records={ledgerTail.records} />
        </section>
      </div>
    </div>
  )
}
