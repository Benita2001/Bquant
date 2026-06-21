---
name: bquant-weekend-drift
description: >
  Detects the price-discovery gap between bStocks (trading 24/7 on-chain) and their
  NYSE/Nasdaq reference prices while markets are closed, accumulating live CMC snapshots
  and emitting mean-reversion signals across five tokens with on-chain logging to BSC testnet.
---

## What this skill does

BQuant Weekend Drift is the core analytical skill for BQuant (BNB Hack, Track 2 — Strategy Skills).

Markets for stocks close on weekends. bStock tokens (tokenised equities on BSC) keep trading.
This creates a price-discovery gap: the on-chain price can drift away from the last known
NYSE/Nasdaq reference price. When the gap is wide enough, a mean-reversion signal fires —
betting that the on-chain price will return to the anchor when markets re-open.

This skill accumulates its own history (no historical OHLCV is available on our plan) by
snapshotting prices via CMC Skill Hub every 30-60 minutes and persisting them to
`data/weekend_snapshots.json`. It then computes drift from the first snapshot (the anchor)
and maps it to a signal.

**Tokens:** NVDAB, TSLAB, CRCLB, MUB, SNDKB

**Drift formula:**
```
drift_t = (price_t - price_t0) / price_t0
```

**Signal thresholds:**

| condition          | signal               |
|--------------------|----------------------|
| `|drift| > 1.5%`  | LONG or SHORT (direction is opposite to drift; reversion bet) |
| `|drift| < 0.3%`  | CONVERGED — exit or don't open |
| else               | FLAT                 |

---

## When to invoke this skill

- When a user or orchestrator asks for the current bStock drift status or weekend signal.
- When a new price snapshot needs to be recorded.
- When the agent needs to decide whether to log a signal to the on-chain registry
  (`registry/BQuantSignalRegistry.sol`).
- **Do not** invoke for intra-week signals; this strategy is weekend-gap only.
- **Do not** use placeholder or synthetic prices — if CMC returns nothing, say so.

---

## Scripts

### `scripts/snapshot_logger.py`

Appends one snapshot entry to `data/weekend_snapshots.json` (project root, created if absent).

**Called by agent runtime** — the agent fetches prices via CMC Skill Hub MCP, then calls:

```python
from skills.bquant_weekend_drift.scripts.snapshot_logger import log_snapshot

# Real snapshot — anchor (t0) captured 2026-06-20T22:46:37.991416+00:00
entry = log_snapshot({
    "NVDAB": 209.56,
    "TSLAB": 400.53,
    "CRCLB": 80.62,
    "MUB":   1131.995,
    "SNDKB": 2240.63,
})
```

Or from the CLI (agent passes prices as a single arg):
```
# Real snapshot — anchor (t0) captured 2026-06-20T22:46:37.991416+00:00
python snapshot_logger.py NVDAB=209.56,TSLAB=400.53,CRCLB=80.62,MUB=1131.995,SNDKB=2240.63
```

### `scripts/drift_engine.py`

Pure functions, no I/O. Call after loading `data/weekend_snapshots.json`.

**`calculate_drift(snapshots, token)`**

```python
import json
from scripts.drift_engine import calculate_drift, generate_signal

with open("data/weekend_snapshots.json") as f:
    snapshots = json.load(f)

drift_result = calculate_drift(snapshots, "NVDAB")
# {
#   "token": "NVDAB",
#   "anchor_price": 209.56,                            # real — t0 captured 2026-06-20T22:46:37.991416+00:00
#   "anchor_timestamp": "2026-06-20T22:46:37.991416+00:00",
#   "current_price": 214.48,                           # illustrative — replace with next real snapshot
#   "current_timestamp": "2026-06-20T23:30:00+00:00",  # illustrative
#   "drift_pct": 0.023479,                             # illustrative (+2.35% drift example)
#   "snapshot_count": 2,
#   "ok": True,
#   "error": None,
# }
```

**`generate_signal(drift_pct)`**

```python
signal_result = generate_signal(drift_result["drift_pct"])
# {
#   "signal": "SHORT",
#   "confidence": 73,
#   "reasoning": "Drift +2.35% exceeds the ±1.5% threshold; mean-reversion to NYSE/Nasdaq anchor expected — signal SHORT.",
# }
```

Both functions return plain dicts — no exceptions on bad data, `"ok": False` or
defensive defaults instead.

---

## Mandatory output format

Every signal the agent emits (to terminal, dashboard, or on-chain call) **must** use
this exact block:

```
[Strategy: BQuant — bStock Weekend Drift]
[Token: <TICKER>]
[Anchor (t0): <price> @ <timestamp>]
[Current Price: <price> @ <timestamp>]
[Drift: x.xx%]
[Signal: LONG/SHORT/FLAT/CONVERGED]
[Confidence: xx%]
[Reasoning: <one sentence>]
```

The `logId` written to `BQuantSignalRegistry.sol` links the on-chain event to this
off-chain reasoning block. Keep `reasoning` to one sentence.

---

## Data integrity rules

- Every number must come from a live CMC Skill Hub call or a confirmed snapshot.
  Nothing mocked, stubbed, or backfilled — ever.
- If a token is missing from a CMC response, log the snapshot without it and flag
  the gap in output. Do not interpolate.
- The dataset is mid-build (14-hour hackathon window), not a full weekend-to-Monday
  series. Be upfront about this in all copy.
