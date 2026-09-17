# Architecture — quant-research-lab

**Date:** 2026-09-17 · **Status:** Mission 1 (design only — no code yet)

## 1. Overview

A miniature quantitative research laboratory: modular, reproducible, paper-only. The architecture
enforces one non-negotiable separation:

```text
LLM      → research / feature layer   (classify, extract, hypothesize, summarize)
QUANT    → prediction                 (regularized models on point-in-time features)
PORTFOLIO→ allocation                 (rank → size under constraints)
RISK     → authority                  (deterministic; REJECT > warn)
EXECUTION→ orders                      (paper endpoint only, every step logged)
```

The LLM never emits an order. The risk engine never uses judgment. The execution engine never
touches a live endpoint.

## 2. Module layout (target)

```text
quant-research-lab/
├── config/
│   ├── universe.yaml        # frozen symbol list (≤30, selection criteria in experiment-design)
│   ├── costs.yaml           # frozen slippage/commission assumptions
│   ├── risk.yaml            # frozen risk limits (§5)
│   └── strategies/          # strategy_v1.yaml, strategy_v2.yaml, ... (versioned)
├── data/
│   ├── raw/                 # byte-identical API responses, append-only (JSONL)
│   ├── features/            # point-in-time feature tables (parquet), with as_of
│   └── integrity/           # leakage tests (see docs/research/data-integrity.md, next mission)
├── news/
│   ├── poller.py            # REST poller (market hours)
│   ├── stream.py            # optional websocket consumer (30-symbol budget)
│   ├── normalize.py         # → canonical event record
│   ├── dedup.py
│   ├── classify.py          # LLM taxonomy classification (schema-validated)
│   └── features.py          # event features + decay + interactions
├── signals/
│   ├── momentum.py  mean_reversion.py  xsectional.py
│   ├── volatility.py  volume.py  regime.py
│   └── __init__.py          # each family: hypothesis docstring + features
├── models/
│   ├── combine.py           # ridge/logistic baseline; trees only if justified
│   └── explain.py           # feature contributions per prediction
├── portfolio/
│   └── construct.py         # rank → expected return → risk → cost → constrained allocation
├── risk/
│   └── engine.py            # deterministic checks; returns ALLOW / REJECT with reason
├── execution/
│   ├── paper.py             # Alpaca paper REST; refuses non-paper endpoints
│   └── ledger.py            # signal → proposal → risk → order → fill → portfolio, all logged
├── research/
│   ├── backtest.py          # walk-forward harness (train/val/test, embargo)
│   ├── event_study.py
│   ├── ablation.py          # models 1–4
│   └── journal/             # append-only hypothesis records
├── reports/
│   └── daily.py             # CLI summary: positions, P&L vs benchmark, sleeve attribution
├── docs/
│   ├── architecture.md
│   └── research/            # quant-framework, experiment-design, news-engine, data-integrity
├── .env.example
├── .gitignore
└── README.md
```

## 3. Data flow (paper-trading loop)

```text
[market hours]
  market-data ws ──► features (as_of=T) ──┐
  news poller ──► events ──► event feats ─┤
                                               ▼
                                    SIGNALS (5 sleeves)
                                               ▼
                                    COMBINE → expected_return, confidence, why
                                               ▼
                                    PORTFOLIO → order proposals
                                               ▼
                                    RISK ENGINE → ALLOW / REJECT (logged)
                                               ▼
                                    PAPER EXECUTION → fills → ledger
                                               ▼
                                    PERFORMANCE vs frozen SPY benchmark
                                               ▼
                                    RESEARCH JOURNAL (KEEP / MODIFY / REJECT)
```

## 4. Backtest / research loop (offline)

Same code paths as the paper loop, driven by `research/backtest.py`: walk-forward splits,
embargo gaps, frozen cost/risk configs, and the paper-vs-backtest divergence check. A strategy
version is a frozen `config/strategies/strategy_vN.yaml` + code commit hash + journal entry.

## 5. Risk engine — deterministic rules (v1, frozen before Day 1)

All values are defaults for discussion; the frozen values go in `config/risk.yaml` before Day 1.
The engine is pure functions: `(proposal, portfolio, market_state) → ALLOW | REJECT(reason)`.

- **Paper-mode gate:** refuse to start unless the trading base URL is exactly
  `https://paper-api.alpaca.markets` and `PAPER_TRADING=true`. Any other endpoint → hard exit.
- **Max position size:** 25% of equity per symbol.
- **Max gross exposure:** 95% of equity (long-only; no leverage).
- **Max daily loss:** 5% of day-start equity → halt all new orders for the rest of the day.
- **Max trades/day:** 10 (turnover control).
- **Min liquidity:** price > $5.00 and 20-day average daily dollar volume > $10M.
- **Max volatility exposure:** no new position if symbol 20-day realized vol (annualized) > 100%.
- **Kill switch:** manual flag file (`KILL`) or any gate failure streak → cancel all open orders, no new orders, page the operator (log + CLI alert).
- **Order sanity:** positive quantity, valid symbol in universe, limit/market only, day time-in-force; fractional quantities allowed.

If the model proposes anything outside these constraints: **REJECT** with a logged reason. No overrides.

## 6. Execution

- Paper only: `https://paper-api.alpaca.markets` (separate keys from live; the program never sees live keys).
- Pipeline per order: `signal → order proposal → risk check → paper order → fill → portfolio update`, each step appended to the ledger with timestamps.
- Fills are simulated by the broker; our slippage assumption (frozen in `config/costs.yaml`) is applied in performance accounting, and paper-vs-backtest divergence is tracked.

## 7. Security

- Secrets never in chat, code, or git. `.env` (real keys) is gitignored; `.env.example` documents names only.
- `PAPER_TRADING=true` default; the program exits if it cannot verify paper mode.
- No automatic path to live trading exists in the codebase — adding one requires a deliberate, reviewed, versioned change (and a conversation with the owner first).
- Paper API keys are requested via the secure vault when needed (later mission), never pasted anywhere.

## 8. Reproducibility

- Fixed random seeds everywhere; seeds recorded in configs.
- Strategy versions (`strategy_v1`, …) with dated rationale for every material change.
- Raw data append-only; features rebuildable from raw + code hash.
- Research journal append-only; failed hypotheses kept.

## 9. Explicitly not built (v1)

No frontend/dashboard (CLI + logs + reports), no live trading, no options/shorts/leverage/margin,
no deep learning, no premium data purchases, no new dependencies beyond the minimal set.

## 10. Minimal dependencies (target)

Python 3.10+, `alpaca-py` (official SDK), `pandas`, `numpy`, `pyyaml`, `scikit-learn` (for ridge/logistic;
trees only if justified), `pytest`. Nothing else without a written reason.

---
*Companion docs: `docs/research/quant-framework.md`, `docs/research/experiment-design.md`, `docs/research/news-engine.md`.*
