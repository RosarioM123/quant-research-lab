# News / Event Engine — design

**Date:** 2026-09-17 · **Status:** Mission 1 (design only — no code, no credentials)

## 1. Objective

Build a real-time(ish) event/news ingestion layer that turns raw headlines into **structured,
timestamped event features** — not sentiment scores. The engine answers "what happened, to whom,
how surprising was it, and how fast does it decay?" — never "headline positive → buy."

## 2. What Alpaca actually provides (researched 2026-09-17)

- **News REST API:** `GET https://data.alpaca.markets/v1beta1/news` on the data endpoint
  (same host as market data; works with paper-account keys). Query params include `symbols`,
  `start`, `end`, `sort`, `limit`, `page_token`.
  — https://docs.alpaca.markets/reference/news-3
- **Article fields** (per API docs): `headline`, `summary`, `author`, `created_at`, `updated_at`,
  `content`, `url`, plus `symbols` (ticker mapping) and a stable article `id`.
- **Websocket news channel** exists on the market-data stream (production data endpoint only —
  no sandbox). The free plan's websocket is limited to **30 symbols**; news subscriptions share
  that budget.
- **Implication for our design:** true push news is available but symbol-capped; the robust free-tier
  path is **REST polling** (e.g., every 60 seconds during market hours, budgeted against 200
  req/min). Our `T0` is therefore **receipt time**, honestly labeled — see §9.

## 3. Pipeline

```text
POLL/STREAM → RAW STORE → NORMALIZE → DEDUP → ENTITY MAP → CLASSIFY
    → SURPRISE EXTRACT → FEATURE EMIT → (price join) → SIGNAL LAYER
```

- **Poll/stream:** one poller process during market hours (09:30–16:00 ET) + optional websocket consumer for the 30-symbol universe. Poller is the source of record.
- **Raw store:** every API response stored byte-identical (JSONL, append-only) *before* any processing. Reprocessing must be reproducible from raw.
- **Normalize:** map to the canonical event record (§4). All timestamps converted to UTC, ISO-8601.

## 4. Canonical event record

```text
event_id        # stable: alpaca article id; dedup key
received_at     # our ingestion timestamp (UTC) — the honest T0
created_at      # article created_at from API (UTC)
updated_at      # article updated_at; revisions tracked, never overwrite
symbols[]       # from API symbols field; validated against universe
headline, summary, author, url, content_ref  # content stored by reference
event_type      # §5 taxonomy
event_direction # positive / negative / neutral / unknown  (relative to the company)
surprise        # §6: {metric, expected, actual, surprise_pct} or null
features        # §8: derived numeric features for the signal layer
source          # alpaca-news-rest | alpaca-news-ws
```

**Timestamp discipline (leakage-critical):**
- Decisions at time T may only use article *versions* with `updated_at ≤ T`.
- `received_at` is the only timestamp the trading path may use for "when did we know it."
- If an article is revised after a trade, the revision is stored as a new version; the backtest replays the original version. This is tested explicitly in `docs/research/data-integrity.md` (next mission).

## 5. Event taxonomy (classification, not sentiment)

The LLM classification layer assigns each event one primary type (multi-label allowed for features,
single primary for attribution):

- **Earnings:** eps_surprise, revenue_surprise, guidance_change, margin_change, management_commentary
- **Corporate actions:** acquisition, divestiture, buyback, offering, leadership_change
- **Regulation/legal:** regulatory_approval, investigation, lawsuit, policy_change
- **Product/technology:** product_launch, major_contract, partnership, technical_breakthrough
- **Macro:** fed, cpi_inflation, jobs, rates, geopolitical
- **Analyst/research:** upgrade, downgrade, price_target_change

Each classified event also gets `event_direction` (positive/negative/neutral/unknown *for the
named company*) and a classifier confidence. Low-confidence classifications are quarantined from
trading features but kept for research.

**Explicitly out of scope for v1:** sarcasm/irony handling, multi-hop causal reasoning, rumor
verification. If the engine cannot classify reliably, it emits `unknown` — an honest null, not a guess.

## 6. Event surprise (expected vs actual)

Markets react to surprises, not to good news. The schema supports:

```text
surprise = { metric: "revenue", expected: 10.0e9, actual: 10.5e9,
             surprise_pct: +5.0, expectation_source: "article_text" }
```

**Rules:**
- `expectation_source` is mandatory: `article_text` (parsed from "beat estimates by X%"),
  `company_guidance` (prior stated guidance), or `null`.
- If no reliable expectation exists, `surprise = null`. **Never fabricate expectations.**
- Reality check for v1: the free tier has **no consensus-estimates feed**, so most events will carry
  direction + type but *no quantified surprise*. The schema is ready; the data usually isn't. The
  ablation tests will show whether type+direction alone carry signal.

## 7. Deduplication

- Primary key: Alpaca article `id`.
- Near-duplicates: same `url` after normalization, or headline similarity (token Jaccard ≥ 0.85)
  within a 24h window across outlets → cluster under one `event_id`, keep all variants as evidence.
- Revisions: same `id` with newer `updated_at` → new version row, linked to the original.

## 8. Event features emitted to the signal layer

Per event (and per symbol for multi-symbol events):

- `event_type` (one-hot over taxonomy), `event_direction` (−1/0/+1), classifier confidence
- `surprise_pct` (nullable), `surprise_direction`
- `novelty`: 1 if first article in cluster, decaying for follow-ups
- `minutes_since_event` at decision time (input to decay model, §9)
- Interaction features (with price/volume/vol/regime at event time) — see experiment-design §8:
  `surprise × momentum`, `surprise × volume_z`, `type × vol_regime`, `direction × market_regime`

## 9. News decay model

A news signal must not stay equally important forever. v1 design:

- Parametric decay candidates to be estimated historically: exponential `w(t) = exp(−t/τ)` with
  τ ∈ {30m, 2h, 1d} as competing hypotheses; also step-decay (full weight 1h, half 1d, zero after).
- The decay parameter is **estimated per event type** from historical data (event study), not assumed.
- The news-speed experiment records price at T0, +1m, +5m, +15m, +30m, +60m per event to fit decay empirically.

## 10. LLM role in this engine (and its limits)

The LLM may: classify events into the taxonomy, extract structured fields (figures, guidance
numbers, direction), propose new event categories from the data, summarize clusters.
The LLM may not: decide trade direction, override the surprise=null rule, or emit anything the
schema cannot validate. Every LLM output is schema-validated; validation failures are logged and
quarantined, never silently coerced.

## 11. What cannot be done on free data (documented limits)

- True low-latency news reaction (we poll; institutions are on wires).
- Quantified surprise for most events (no consensus feed).
- Pre-market/overnight event timing precision beyond article `created_at`.
- Verification of rumors; detection of coordinated promotion.
- Full-tape volume context (IEX-only).

---
*Companion docs: `docs/research/experiment-design.md` (§8, §12, §13), `docs/architecture.md`.*
