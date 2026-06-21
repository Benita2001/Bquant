# AGENTS.md

Context for any agent (Claude Code or otherwise) working in this repo.

## What this is

BQuant — a Track 2 (Strategy Skills) submission for BNB Hack. Detects and signals on the
price-discovery gap between bStocks (24/7 on-chain trading) and their NYSE/Nasdaq reference
price (closed most of the week).

Budget: ~14 hours. Optimize for one thing working end-to-end over many things half-working.
Every number in this repo comes from a live API call or a confirmed on-chain tx. Nothing is
mocked, stubbed, or backfilled — if data isn't available yet, the output says so.

## Strategy

Tokens: NVDAB, TSLAB, CRCLB, MUB, SNDKB.

Historical OHLCV is not available to us (REST historical endpoint 403s on our plan; Skill Hub
has no time-anchored query). So the agent generates its own history: snapshot now, snapshot
again every 30–60 min, log to `data/weekend_snapshots.json` (append-only).

```
drift_t = (price_t - price_t0) / price_t0
```

| condition | signal |
|---|---|
| `\|drift\| > 1.5%` | LONG/SHORT, direction = sign of drift (betting on reversion to anchor) |
| `\|drift\| < 0.3%` | converged / exit |
| else | FLAT |

Every signal emits:

```
[Strategy: BQuant — bStock Weekend Drift]
[Token: <TICKER>]
[Anchor (t0): <price> @ <timestamp>]
[Current Price: <price> @ <timestamp>]
[Drift: x.xx%]
[Signal: LONG/SHORT/FLAT]
[Confidence: xx%]
[Reasoning: <one sentence>]
```

Don't change the formula, thresholds, or token list without explicit sign-off — this has
already been through two pivots, see commit history / prior handover doc if curious why.

## Layout

```
data/      snapshot_logger.py, weekend_snapshots.json (cron'd on the Contabo VPS)
sdk/       drift + signal logic as an importable package, stable JSON in/out
registry/  BQuantSignalRegistry.sol, deployed to BSC testnet
website/   static dashboard reading registry + snapshot data
```

`sdk/` is the actual deliverable for "pluggable" — a clean local package any execution agent
can import and call, not a published package with versioning. Don't oversell it.

`website/` is a results dashboard, not a marketing site.

## Sponsor integrations

- **CMC Skill Hub (MCP)** — data source for snapshots. Connected, tested.
- **`bnbagent` (ERC-8004)** — register BQuant's on-chain agent identity, gas-free on BSC
  testnet via paymaster. Identity layer only — unrelated to the signal registry contract below.
- **TWAK, Mode B (WalletConnect)** — read-only connection to an existing Trust Wallet holding
  bStocks, `twak wallet portfolio`. Not Mode A — no autonomous wallet, no execution, no custody
  risk. Track 2 doesn't require live trading; don't build past what's needed.

## Signal registry contract

`registry/BQuantSignalRegistry.sol`. `logSignal(token, signal, driftBps, confidence)`, emits
`SignalLogged`. `confidence` 0–100. Reasoning text stays off-chain — on-chain proves what
happened, the README/demo carries why, joined by `logId`. This is the single highest-weight
judging item (on-chain piece must be real, not cosmetic). If time runs out, cut the website
before this.

## Rules

- No placeholder or synthetic data, anywhere, ever — dashboard, demo, README included.
- Don't resurrect the earlier ADX/ATR/RSI regime-classifier idea. Different project.
- Verify a data source returns what you need before writing logic against it.
- Say so immediately if something doesn't work. Don't route around a broken piece silently.
- Be upfront in all copy that the dataset is mid-drift, captured live during a 14-hour build —
  not a full weekend-to-Monday convergence series.