# BQuant Weekend Drift — Strategy Specification

**Version:** 1.0  
**Status:** Active (BNB Hack Q2 2026, Track 2)  
**Readable by:** judges, auditors, or any agent without access to the code

---

## 1. Thesis

Tokenised equities (bStocks) on BNB Chain trade continuously, 24/7. Their underlying
references — NYSE and Nasdaq-listed stocks — only trade during exchange hours (~9:30am–4pm ET,
Monday–Friday). Over a weekend, the on-chain price of a bStock can drift away from the last
known reference price.

**Hypothesis:** This drift is transient. When NYSE/Nasdaq re-opens on Monday, the on-chain
price mean-reverts to the reference anchor. A sufficiently large drift during market closure
is therefore a statistically motivated mean-reversion signal.

This strategy does not predict direction in the conventional sense — it bets on gravitational
pull back toward a known fundamental reference point (the reference stock's closing price).

---

## 2. Tokens

| Symbol | Underlying Reference |
|--------|----------------------|
| NVDAB  | NVIDIA Corp (NVDA)   |
| TSLAB  | Tesla Inc (TSLA)     |
| CRCLB  | Circle Internet (CRCL) |
| MUB    | Micron Technology (MU)              |
| SNDKB  | SanDisk Corp (SNDK)  |

Token contracts are on BNB Chain. Prices are sourced from CMC Skill Hub (MCP tool).

---

## 3. Data Method — Path B (Self-Generated History)

Historical OHLCV for bStock tokens is **not available** on the current CMC plan (REST
historical endpoint returns 403; Skill Hub has no time-anchored price query). Therefore:

- The agent snapshots current prices via CMC Skill Hub on a recurring basis (every 30–60
  minutes, cron-driven on Contabo VPS).
- Each snapshot is appended to `data/weekend_snapshots.json` as:
  ```json
  {
    "timestamp": "2026-06-20T14:00:00+00:00",
    "prices": {
      "NVDAB": 135.20,
      "TSLAB": 242.10,
      "CRCLB": 18.45,
      "MUB": 106.30,
      "SNDKB": 72.80
    }
  }
  ```
- The **first** snapshot in the file is the anchor (`t0`). All drift calculations are
  relative to this anchor.

**Known limitation:** The dataset window is bounded by the hackathon build period (~14 hours).
This is not a full weekend-to-Monday convergence series. The drift trajectory and signal
quality improve the longer the cron runs. Any backtest or evaluation must account for this
cold-start constraint.

---

## 4. Drift Formula

```
drift_t = (price_t − price_t0) / price_t0
```

Where:
- `price_t0` = price of the token in the first snapshot (the anchor)
- `price_t`  = price of the token in the most recent snapshot

`drift_t` is a signed fractional value (positive = price moved up from anchor,
negative = moved down). It is expressed as a percentage in all outputs.

---

## 5. Signal Thresholds

| Condition             | Signal    | Direction logic                               |
|-----------------------|-----------|-----------------------------------------------|
| `\|drift\| > 1.5%`   | LONG or SHORT | Direction is **opposite** to drift sign (reversion bet): drift up → SHORT; drift down → LONG |
| `\|drift\| < 0.3%`   | CONVERGED | Price has returned to anchor; exit or skip    |
| `0.3% ≤ \|drift\| ≤ 1.5%` | FLAT | Insufficient edge; no position                |

Thresholds are hard-coded in `drift_engine.py` and must not be changed without explicit
sign-off (two prior pivots have already settled this calibration).

---

## 6. Confidence Scoring

Confidence is a 0–100 integer included in every signal output.

| Signal    | Confidence calculation |
|-----------|------------------------|
| LONG/SHORT | 60 at threshold (1.5%), scales linearly to 85 at 3× threshold (4.5%), capped at 85 |
| FLAT       | Fixed 50 (no directional edge) |
| CONVERGED  | Fixed 90 (strong mean-reversion completion evidence) |

This is not a statistical p-value — it is an ordinal confidence band for on-chain logging
and human-readable output. The registry contract stores it as an integer 0–100 (`confidence`
field in `logSignal`).

---

## 7. Signal Output Format

Every signal emitted by the system must include this reasoning block, verbatim:

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

The `logId` emitted by `BQuantSignalRegistry.logSignal()` on BSC testnet links the on-chain
event to this off-chain block. The reasoning text is intentionally kept off-chain to minimise
gas and because the README/demo carries the narrative; the chain proves *what* was logged.

---

## 8. On-Chain Registry

Contract: `registry/BQuantSignalRegistry.sol`  
Network: BSC Testnet  
Entry point: `logSignal(token, signal, driftBps, confidence)`  
Event emitted: `SignalLogged(logId, token, signal, driftBps, confidence, timestamp)`

`driftBps` is the drift expressed in **basis points** (integer), e.g. `drift_pct * 10_000`.
Reasoning text is not stored on-chain.

---

## 9. Known Limitations

| Limitation | Implication |
|------------|-------------|
| No historical OHLCV (Path B data method) | Anchor is set at first runtime snapshot, not market close Friday. Weekend-open gap is partially captured, not precisely measured. |
| 14-hour dataset window | Signal quality improves over time; early signals have fewer supporting snapshots. |
| Single anchor point | No rolling-window baseline; a mis-timed first snapshot becomes the permanent anchor. |
| CMC Skill Hub latency / gaps | If a token is missing from a CMC response, that snapshot is partial. Missing tokens are flagged in output, not interpolated. |
| No live execution | Track 2 requires a signal, not a trade. The system does not open positions, manage risk, or interact with a DEX. |

---

## 10. Out of Scope

- ADX / ATR / RSI regime classification (prior pivot, abandoned)
- Autonomous wallet / custody (TWAK Mode B is read-only; no Mode A)
- Published PyPI package (sdk/ is a local importable module, not versioned)
- Live NYSE/Nasdaq price feed (reference anchor is the last known price embedded in the
  bStock oracle, not a direct market data subscription)
