# Quantitative Research Framework

**Project:** quant-research-lab — a miniature quantitative research laboratory for a $100, 30-day paper-trading experiment.
**Date:** 2026-09-17 · **Status:** Mission 1 (research & design only — no code, no trades)

## 1. Purpose

This document distills **general, publicly documented research principles** from three sophisticated
systematic firms — Citadel (Global Quantitative Strategies / Equity Quantitative Research),
Point72 (Cubist Systematic Strategies), and Two Sigma — as *inspiration* for how to run a small,
honest quantitative research process.

**What this is not:**
- It does not reproduce, reverse-engineer, or claim to approximate any firm's proprietary strategy.
- None of the sources below describe actual signals, model architectures, lookbacks, instruments, or parameters. None were sought.
- Every principle below is at the *process* level: how to do research, not what to trade.

Where a claim is our own inference for a retail-scale experiment (rather than something a firm
actually said), it is labeled **[inference]**. Everything else is paraphrase of public material, cited.

## 2. The shared doctrine

Across different vocabularies, all three firms publicly describe essentially the same systematic
research doctrine:

1. **The scientific method is the operating system.** Hypotheses first; measurement, learning, and adjustment after.
2. **Edge comes from many small, economically plausible signals**, not one big bet.
3. **Backtests are hypothesis tests, not truth.** A backtest is only valid insofar as the live implementation matches the backtest's assumptions.
4. **Portfolio construction and execution are optimization problems** — expected return vs. risk vs. trading cost — not afterthoughts.
5. **Data is a breadth game.** Relentlessly source and evaluate diverse datasets.
6. **Research infrastructure is a source of alpha.** Backtest speed and reproducibility change researcher behavior.
7. **Culture is collaborative, experimental, academic-adjacent.** Small teams, shared tooling, real-money scoreboards.

## 3. Per-firm principles (public sources)

### 3.1 Citadel — Global Quantitative Strategies / Equity Quantitative Research

GQS is Citadel's quantitative investment business, founded 2012 (head: Navneet Arora since 2019).
EQR is its systematic equities platform.

- **Economically grounded signals.** EQR's edge is described as "identifying subtle, economically grounded signals" — structural insight plus advanced modeling plus large-scale engineering. Signals must be robust, systematic, and economically grounded, not statistical curiosities.
  — https://www.citadel.com/careers/quantitative-research/
- **Hypotheses first, then risk, then construction.** "We research, analyze risk and construct portfolios based on our hypotheses."
  — https://www.citadel.com/careers/quantitative-research/
- **Fast, iterative, market-feedback-driven research.** Research is "fast, iterative, and grounded in economic intuition"; researchers iterate models using market feedback. One practitioner description: the process is "deeply non-linear… a lot of noise," and the goal is "something systematic and robust with good metrics to judge it by."
  — https://www.citadel.com/careers/quantitative-research/ ; https://www.efinancialcareers.com/news/citadel-quant-day-in-the-life
- **The research platform is an alpha enabler.** Quantitative developers own both the production pipeline and the research platform. "If a backtest takes two minutes instead of sixty, that changes the way people think. It creates more room for creativity and discovery." The accuracy, speed, and adaptability of systems "determine how quickly insights move from hypothesis to production."
  — https://www.citadel.com/careers/career-perspectives/richard-lee-on-being-a-quantitative-developer/
- **Portfolio construction as large-scale optimization.** GQS researchers do "construction of a complex multi asset portfolio by utilizing large scale portfolio optimization techniques" and develop "sophisticated optimization algorithms."
  — https://www.citadel.com/careers/details/global-quantitative-strategies-quantitative-researcher/
- **Data in all forms.** Citadel "continually seek[s] data in all forms to generate insights, validate our ideas or identify new opportunities," with a central Data Strategies Group doing AI/ML modeling on noisy alternative datasets.
  — https://www.citadel.com/careers/quantitative-research/
- **Appetite for differentiated inputs (press-reported).** Bloomberg/Hedgeweek reported GQS preparing a program to pay external funds for trading ideas to integrate into systematic models; Arora is on record that GQS "has long combined quantitative research with discretionary inputs." (Program itself not firm-confirmed.)
  — https://www.hedgeweek.com/citadel-expands-quant-platform-with-new-hedge-fund-signal-sharing-initiative/

### 3.2 Point72 — Cubist Systematic Strategies

Cubist is Point72's systematic affiliate deploying "systematic, computer-driven trading strategies
across multiple liquid asset classes, including equities, futures and foreign exchange"; its
systematic business dates to 1994 (head: Geoffrey Lauprete).

- **The most explicit public pipeline of the three.** Job postings enumerate the research pipeline as: *data processing → feature design → model training → portfolio construction and management → back-testing → performance analysis*, with a full lifecycle of *idea generation → hypothesis development and testing → alpha discovery → trading strategy generation → backtesting → portfolio analysis*.
  — https://point72.com/cubist/ ; Point72 Greenhouse job postings (QR roles)
- **Rigorous anomaly research on public data.** "The core of our effort is rigorous research into a wide range of market anomalies, fueled by our unparalleled access to a wide range of publicly available data sources."
  — Point72 Cubist job postings
- **Anti-overfitting as stated craft.** A Cubist research analyst: "It's an open-ended problem that challenges you to find something real, and not just a statistical artifact. There's an art to figuring out what's important."
  — https://point72.com/cubist/
- **Costs enter the model, not just the backtest.** Investment models "explicitly forecast risk, return, and trading costs." Automated execution is overseen with transaction-cost monitoring; portfolio risk is managed dynamically on historical *and* real-time performance.
  — Point72 Cubist job postings (PM roles)
- **Dataset evaluation as a discipline.** Researchers "evaluate new datasets for alpha potential," "search for signals in the noise," and follow current academic research.
  — https://point72.com/cubist/ ; Point72 Cubist job postings
- **Experimental culture with a dollar scoreboard.** "We are experimental and iterative in our approach to generating predictive insights and taking risk, with a scoreboard that moves in dollars and cents." Shared tooling: "share wheels, not re-invent them."
  — https://point72.com/cubist/

### 3.3 Two Sigma

Founded 2001 by David Siegel and John Overdeck; self-described as applying "a rigorous
scientific-method based approach to investment management"; mission "to find value in the world's data."

- **The scientific method, stated most explicitly.** Siegel (2017 WSJ op-ed): the most effective way to address "hard problems like forecasting asset prices or optimizing portfolios" is the scientific method — it brings rigor and counteracts "common but harmful cognitive and emotional biases." Everything "from data ingestion to trade execution" should rest on "carefully crafted hypotheses, followed by a recurring process of measurement, learning, and adjustment."
  — https://www.twosigma.com/articles/wsj-op-ed-by-david-siegel-investing-and-the-scientific-method/
- **Three operating pillars** (official article): data-driven decision-making; hypothesis testing ("a culture of experimentation; ideas tested and refined based on real-world results"); iterative process ("even the most successful strategies require continuous evaluation and adaptation").
  — https://www.twosigma.com/articles/the-innovation-equation-curiosity-x-the-scientific-method-at-two-sigma/
- **Backtests are hypothesis tests.** "We want to ensure that our conception of reality going forward adheres to what we thought happens historically, the parameters of our back tests." **[This is our central backtesting discipline: the live implementation must match the backtest's assumptions, or the backtest is void.]**
  — https://www.twosigma.com/articles/the-innovation-equation-curiosity-x-the-scientific-method-at-two-sigma/
- **Execution as experiment.** Two Sigma runs randomized A/B trials on execution algorithms, collecting data "over days, weeks, and months" to detect real differences.
  — https://www.twosigma.com/articles/the-innovation-equation-curiosity-x-the-scientific-method-at-two-sigma/
- **Diverse models from a common platform.** Public pension-board characterization (2016, dated): a diversified portfolio of long and short positions from "a diverse set of longer-term fundamental and technical models" on a common research platform — fundamental models on public data (value, quality, yield), technical models on price/volume capturing behavioral biases like trend; "rigorous testing… to create models that identify and profit from trading persistent relationships" (note: *persistent* relationships).
  — PA PSERS 2016 board document (third-party, dated)
- **Risk-factor discipline: holistic, parsimonious, orthogonal, actionable.** Stated for Two Sigma's public Factor Lens (Venn), not internal alpha models — but directly usable as our risk/anti-overfit discipline: decompose risk into few, uncorrelated, explainable, tradable pieces.
  — https://www.venn.twosigma.com/resources/introducing-the-two-sigma-factor-lens
- **Culture: curiosity × scientific method** as a "common language" across disciplines.
  — https://www.twosigma.com/articles/the-innovation-equation-curiosity-x-the-scientific-method-at-two-sigma/

## 4. Principle → experiment translations [inference]

How each public principle becomes a concrete rule in this $100 paper-trading lab. These translations
are our own design choices, not claims about the firms.

| Public principle | Our rule |
|---|---|
| Hypothesis-first research | Every signal family ships with a written hypothesis (why should this work, economically?) in `docs/research/` *before* its backtest runs. No hypothesis, no backtest. |
| Backtest = hypothesis test | Walk-forward only; chronological splits; every feature timestamped; live/paper implementation must match backtest assumptions or the backtest is discarded. See `docs/research/experiment-design.md`. |
| "Something real, not just a statistical artifact" | Require economic rationale + out-of-sample confirmation + parsimony. Ablation tests (price-only vs news-only vs combined vs full) for every claimed contribution. |
| Many small signals, not one bet | Five independent strategy sleeves (momentum, mean reversion, news/event, regime, ensemble). Attribution per sleeve; the ensemble may not hide a bad sleeve. |
| Forecast risk, return, *and costs* | Slippage/commission assumptions are explicit model inputs, documented in `docs/research/experiment-design.md`, not post-hoc adjustments. |
| Portfolio construction as optimization | Rank → size by expected return vs. risk vs. cost under hard constraints (position limits, exposure, diversification). Never "buy the top-ranked stock." |
| Execution as experiment | Paper fills logged with timestamps; paper-vs-backtest slippage tracked as its own metric; news-speed experiment measures signal decay explicitly. |
| Data breadth | Start with clean public data (Alpaca free tier); maintain a dataset evaluation log — every new dataset gets a dated entry with what was tested and the verdict. |
| Research platform as alpha | Invest early in a fast, reproducible backtest harness. Reproducibility (seeds, versioned strategies, frozen configs) is a first-class requirement. |
| Dollar-denominated scoreboard | One frozen benchmark (buy-and-hold SPY, same $100, set before trading starts, never changed). Paper P&L vs. benchmark is the scoreboard. |
| Holistic, parsimonious, orthogonal, actionable | Prefer few, uncorrelated signals; check signal correlations before combining; every position must map to an explainable signal contribution ("why did the model predict this?"). |
| Curiosity × scientific method | Research journal is append-only. Failed hypotheses are kept — they are the record. See `docs/research/experiment-design.md` § Research journal. |

## 5. What we explicitly do NOT claim

- We do not claim to reproduce, approximate, or compete with any of these firms' strategies.
- We do not have their data, infrastructure, execution, or capital. Our constraints (free-tier IEX-only data, 30-symbol websocket limit, REST-polled news, retail paper fills) are documented in `docs/research/experiment-design.md` and bound what we can conclude.
- A 30-day, $100 experiment cannot distinguish skill from luck with high confidence. The honest output of this lab is *measured evidence about specific signals*, not a verdict on "beating the market."

## 6. Limitations of this research

- No proprietary signals or parameters exist in public sources (by design); everything above is process-level.
- Some Citadel material (alternative-data article, one practitioner interview) was read via search snippets, not full pages.
- Two Sigma's most concrete process description is a dated (2016) third-party pension document.
- No public leadership interview on research philosophy was found for Cubist; its principles come from the official page and job postings.
- The GQS external-signal program is press-reported, not firm-confirmed.

---
*Sources researched 2026-09-17. Full per-firm source notes are retained in the project's research archive.*
