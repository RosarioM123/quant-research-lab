# SIGNAL — quant-research-lab

A miniature quantitative research lab: a systematic **$100 paper-trading
experiment** run over 30 calendar days. SIGNAL is the software; the experiment
has **not** been run. Everything here is code, tests, and fixtures — no real
trading, no real money, no performance claims.

> **Paper trading only. No real money. Ever.** The execution layer refuses to
> address any endpoint except `https://paper-api.alpaca.markets`, and refuses
> to start at all unless `PAPER_TRADING=true`.

## Architecture

```
LLM       -> research / feature extraction ONLY (never orders, never positions)
QUANT     -> prediction (signal families + ridge combiner)
PORTFOLIO -> allocation (rank -> expected return -> risk -> cost -> size)
RISK      -> deterministic authority (ALLOW / REJECT, stable reason codes)
EXECUTION -> paper orders only (simulated fills, hash-chained ledger)
```

The LLM layer is structurally barred from trading: `llm/research.py` raises
`LLMBoundaryViolation` if anything asks it to emit an order or control a
position. The risk engine (`risk/engine.py`) is pure and deterministic — no
judgment, no overrides. Every pipeline step is appended to a SHA-256
hash-chained ledger (`signal -> proposal -> risk_decision -> order -> fill ->
position`), independently verifiable by the C# tool in `tools/LedgerVerify/`.

## Hard constraints (encoded in code, tested)

- Exactly **$100** simulated capital; exactly **30 calendar days**
- **Long-only** — shorting is structurally impossible (SELL capped at held qty)
- **No leverage, no margin, no derivatives/futures/options**
- No prices below **$5**; max **25%** of equity per symbol; max **95%** gross exposure
- **Frozen SPY buy-and-hold** benchmark
- Chronological backtests only; no look-ahead (point-in-time features carry `as_of`)
- Kill-switch file halts all trading

## Layout

| Path | Language | What |
|---|---|---|
| `config/` | YAML + Python | Validated configs, SHA-256 freeze/manifest |
| `data/` | Python | Raw store (JSONL), point-in-time features, leakage guards |
| `news/` | Python | Poller, normalize, dedup (revision retention), stub classifier, features |
| `signals/` | Python | momentum, mean-reversion, cross-sectional, volatility, volume, regime |
| `models/` | Python | Ridge combiner (numpy closed-form), feature-contribution explainability |
| `portfolio/` | Python | Constrained long-only construction |
| `risk/` | Python | Deterministic ALLOW/REJECT engine + paper-mode gate |
| `execution/` | Python | Paper broker (endpoint gate), hash-chained ledger |
| `backtest/` | Python | Chronological no-look-ahead replay |
| `llm/` | Python | Research-only helpers; order/position calls raise |
| `tests/` | Python | 76 pytest tests (all rejections, tampering, leakage, replay) |
| `dashboard/` | React + Sass | Experiment dashboard, fixture data only, no backend |
| `tools/LedgerVerify/` | C# (.NET 8) | Independent ledger + constraint verifier |
| `docs/` | Markdown | Architecture and research design documents |

## Python: run the tests

```bash
python3 -m venv .venv
.venv/bin/pip install numpy pandas pyyaml pytest
.venv/bin/python -m pytest tests/ -q
```

## Dashboard

The dashboard renders committed fixture data only (generated from the replay
pipeline on synthetic seeded prices — clearly labeled "fixture" in the UI).
No backend, no real data.

```bash
cd dashboard
npm install
npm run build      # outputs dist/ (gitignored; rebuild anytime)
npm run dev        # local preview
```

Regenerate fixtures: `../.venv/bin/python dashboard/scripts/generate_fixtures.py`

## C# ledger verifier

```bash
cd tools/LedgerVerify
dotnet run -- /path/to/ledger.jsonl
```

Written for .NET 8, stdlib only. **Not compiled locally** — the build machine
had no .NET SDK; see `tools/LedgerVerify/README.md`.

## CI

`.github/workflows/ci.yml` runs the Python test suite and the dashboard
`npm install` + `npm run build` on every push/PR.

## Research docs

- `docs/architecture.md` — system boundaries
- `docs/research/experiment-design.md` — the 30-day experiment protocol
- `docs/research/news-engine.md` — news pipeline design
- `docs/research/quant-framework.md` — signal/model methodology

License: proprietary — see `LICENSE` (unchanged).
