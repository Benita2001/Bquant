# BQuant

BQuant is an LLM Skill that detects and signals on the price-discovery gap between bStocks (tokenized US equities trading 24/7 on BNB Chain) and their reference market  NYSE/Nasdaq which is closed on the weekends.
**Track 2: Strategy Skills**.

Every signal the skill produces is logged on-chain, 
---

## The thesis

bStocks (NVDAB, TSLAB, CRCLB, MUB, SNDKB) launched on BNB Chain on 2026-06-12 and trade 24/7.
Their underlying reference price the real NVIDIA, Tesla, Circle, Micron and SanDisk shares
they're backed 1:1 by  only trades when NYSE/Nasdaq is open, roughly 9:30am–4pm ET,
Monday–Friday. Outside those hours, bStock prices can drift from "true" price with no real
market to correct them. BQuant measures that drift in real time and signals a convergence trade anticipating reversion once the real market reopens.

---

## Install

Add BQuant to any Claude or Skill-compatible agent in one step paste this into your agent:

> Fetch the BQuant Skill from https://github.com/Benita2001/Bquant and install it into my Skills directory.

Or manually:

```bash
git clone https://github.com/Benita2001/Bquant.git
cp -r Bquant/skills/bquant-weekend-drift /path/to/your/skills/directory/
```


## How it works

```
drift_t = (price_t - price_t0) / price_t0
```

| condition | signal |
|---|---|
| `\|drift\| > 1.5%` | LONG / SHORT — direction = sign of drift, betting on reversion to anchor |
| `\|drift\| < 0.3%` | converged / exit |
| otherwise | FLAT |

Every signal is emitted in a fixed reasoning-block format:

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

**Why self-logged data, not historical OHLCV:** 
 BQuant builds its own historical record: it polls live
prices on a fixed interval and logs each snapshot itself rather than querying for a past that isn't available to it. Every number in this repo is either a live API response or a confirmed
on-chain transaction. 

---

## Live deployments

**BSC Testnet (chain ID 97)**

| Contract | Address |
|---|---|
| BQuantSignalRegistry | `0xFFCC472c47cf0a8168545a8318832950f7C6F453` |

[View on BscScan](https://testnet.bscscan.com/address/0xFFCC472c47cf0a8168545a8318832950f7C6F453) ·
Deploy tx: [`0x297901...26e7203`](https://testnet.bscscan.com/tx/0x29790132a2390675657dfe509a9823975d7286b9bb3d9f6417c88c10226e7203)

**ERC-8004 agent identity**

| Field | Value |
|---|---|
| Agent | `bquant-weekend-drift` |
| Agent ID | `1470` |
| Network | BSC Testnet |

[View registration tx](https://testnet.bscscan.com/tx/0x7d2485eaaef6d3e11426b384a608802b63d1dd18e08f7978c3d860dd2cb7c16f)

**Signals logged on-chain** (`totalLogs() = 5`, independently verified via `cast call`)

| Token | Signal | Drift (bps) | Confidence | Tx |
|---|---|---|---|---|
| NVDAB | FLAT | -4 | 90% | [view](https://testnet.bscscan.com/tx/0x59560eb4162e2cb909d5e27f063786e43757da3cba4b84ffef5fcdd146199e0a) |
| TSLAB | FLAT | +8 | 90% | [view](https://testnet.bscscan.com/tx/0x14a2441bdbc4a651ff0a2d28d40dc8947c0fa93067775cc2bcffbbf630f10f7f) |
| CRCLB | FLAT | +5 | 90% | [view](https://testnet.bscscan.com/tx/0x784fdd5c8c821416419aae3250d21e82da134193d926e4d2ae3cc824770b1dda) |
| MUB | FLAT | +26 | 90% | [view](https://testnet.bscscan.com/tx/0x491fb03ee3f42c3c55cb5bd3da156abd23b3024958c3094bfc3ca488ecbf92df) |
| SNDKB | FLAT | +12 | 90% | [view](https://testnet.bscscan.com/tx/0xf9b8830116ef27b3ef7046dcd48817fcf3a387540675fce63750780f33bd3038) |

All five read FLAT because data collection started mid-build  drift hasn't had time to build
past the 0.3% convergence threshold yet. This is honest, not a limitation we're hiding: the
`logId` in each `SignalLogged` event is the join key back to the off-chain reasoning block, and
anyone can re-run the same query against the contract to confirm these are real, not staged.

---

## The Skill

BQuant is authored as a real LLM Skill, not just a script with a description attached:

```
skills/bquant-weekend-drift/
├── SKILL.md                  # what the skill does, when to invoke it, how to call it
├── scripts/
│   ├── tokens.py              # single source of truth for live bStock tickers
│   ├── snapshot_logger.py     # polls CMC Skill Hub, appends to data/weekend_snapshots.json
│   ├── drift_engine.py        # calculate_drift() / generate_signal() — pure, JSON in/out
│   └── run_snapshot.sh        # cron-callable wrapper, used on a 30-minute schedule
└── references/
    └── strategy_spec.md       # full backtestable strategy spec, readable without the code
```

`drift_engine.py` is the actual "pluggable" deliverable — any execution agent can import
`calculate_drift()` and `generate_signal()` directly, no external state, plain dicts in and out.

---

## Using this Skill

BQuant follows the standard Skill format (`SKILL.md` + `scripts/` + `references/`), so it can
be dropped into any Skill-compatible agent not just used standalone in this repo.

**Option 1 — load it as a Claude Skill**

Copy `skills/bquant-weekend-drift/` into your own Skills directory (e.g. `/mnt/skills/user/`
or wherever your Claude environment loads Skills from). Claude reads `SKILL.md`'s frontmatter
(`name`, `description`) to know when to invoke it — for example, any prompt mentioning bStocks,
weekend drift, or one of the five tracked tickers (NVDAB, TSLAB, CRCLB, MUB, SNDKB) will
surface this Skill automatically. No code changes required.

**Option 2 — call the engine directly from your own agent**

You don't need the Skill format at all if you just want the signal logic. Copy
`scripts/drift_engine.py` and `scripts/tokens.py` into your project and import directly:

```python
from drift_engine import calculate_drift, generate_signal

# snapshots is a list of {"timestamp": ..., "prices": {...}} dicts —
# capture your own via snapshot_logger.py, or supply your own price history
drift = calculate_drift(snapshots, "NVDAB")
signal = generate_signal(drift["drift_pct"])

print(signal)
# {"signal": "FLAT", "confidence": 90, "reasoning": "..."}
```

Both functions are pure — plain JSON-serializable dicts in, plain dicts out, no global state,
no hidden network calls. This is what makes the Skill genuinely pluggable into any execution
agent: a Track 1-style trading agent could call `generate_signal()` and act on the result
without touching anything else in this repo.

**Option 3 — run the full pipeline yourself**

Clone the repo, set `CMC_MCP_API_KEY` in your environment, and run `snapshot_logger.py` on a
schedule (cron or otherwise) to build your own live dataset, independent of ours. The on-chain
Signal Registry contract is open — anyone can deploy their own instance from
`registry/src/BQuantSignalRegistry.sol` and log signals against it, or read ours directly at
`0xFFCC472c47cf0a8168545a8318832950f7C6F453` without deploying anything.

**Requirements**

- Python 3.10+
- A CoinMarketCap API key (free tier works same key serves both the Skill Hub MCP and the
  REST `quotes/latest` endpoint used for snapshots)
- No BNB Chain wallet needed unless you want to log your own signals on-chain

---

## Sponsor stack

| Sponsor | Used for | Real, not cosmetic because |
|---|---|---|
| CoinMarketCap AI Agent Hub | Live snapshot data via Skill Hub MCP, all 5 tokens | `weekend_snapshots.json` grows every 30 minutes from a real cron job on a live VPS |
| BNB AI Agent SDK | ERC-8004 agent identity registration | Real `agentId 1470`, real tx hash, gas-free via MegaFuel paymaster |
| BNB Chain | Signal Registry deployment + execution venue for bStocks | Custom contract, deployed and called live on BSC testnet, independently verified via `cast call` |

The Signal Registry contract is our own — written and deployed directly, not generated by the
BNB AI Agent SDK, since that SDK's scope is agent identity (ERC-8004) and agent-to-agent
commerce (ERC-8183), not arbitrary contract deployment.

---

## Token universe

Five bStocks are live on BNB Chain as of this build (verified directly against CMC and the
official Binance bStocks announcement, not assumed):

| Ticker | Underlying |
|---|---|
| NVDAB | NVIDIA Corp |
| TSLAB | Tesla Inc |
| CRCLB | Circle Internet Group |
| MUB | Micron Technology |
| SNDKB | SanDisk Corp |

A sixth, SPCXB (SpaceX), is listed on bstocks.finance but explicitly marked "planned for
trading, pending SpaceX's public listing on Nasdaq" — not live, so it's excluded from
`tokens.py` by status flag, not by omission. When it goes live, enabling it is a one-line
change, not a rebuild.

---

## Architecture

BQuant has two halves: a data pipeline that builds the signal (left), and the Skill interface
any agent calls to consume it (right). The two only talk to each other through
`drift_engine.py` — that's the seam.

```
  BQuant's own pipeline                    Any external agent
  ───────────────────────                  ───────────────────────

  CMC Skill Hub (MCP)
        │
        ▼
  snapshot_logger.py (cron, 30 min)
        │
        ▼
  data/weekend_snapshots.json
        │
        ▼
  drift_engine.py  ◄────────────────────►  from drift_engine import \
  calculate_drift()                          calculate_drift, generate_signal
  generate_signal()                        drift = calculate_drift(snaps, "NVDAB")
        │                                   signal = generate_signal(drift["drift_pct"])
        ▼                                   # {"signal": "LONG", "confidence": 85, ...}
  BQuantSignalRegistry.sol (BSC testnet)            │
  logSignal()                                       ▼
                                            agent decides what to do with the signal:
                                            trade it, log it, alert on it, ignore it —
                                            BQuant doesn't care, it just hands back JSON
```

**What happens when another agent uses the Skill:**

1. The agent loads `skills/bquant-weekend-drift/` (via `SKILL.md`'s frontmatter, or by
   importing `drift_engine.py` directly — see [Using this Skill](#using-this-skill)).
2. It supplies its own price snapshots, or reuses BQuant's `data/weekend_snapshots.json`
   if it just wants our live feed.
3. It calls `calculate_drift()` then `generate_signal()` — two pure functions, no network
   calls, no side effects, no shared state with BQuant's own pipeline.
4. It gets back a plain JSON dict: `signal`, `confidence`, `reasoning`. What it does with
   that — trade it, log it to its own contract, surface it to a human is entirely up to
   the calling agent. BQuant's job ends at the signal.

This is why the Skill is genuinely pluggable: a Track 1-style autonomous trading agent could
call `generate_signal()` inside its own decision loop and act on the result without touching
anything else in this repo, including our on-chain registry that part is BQuant's own proof
layer, not a dependency the calling agent needs.

---

## Running it

```bash
# Capture a snapshot manually
CMC_MCP_API_KEY=<your_key> bash skills/bquant-weekend-drift/scripts/run_snapshot.sh

# Compute drift / signal for a token
python3
>>> from skills.bquant_weekend_drift.scripts.drift_engine import calculate_drift, generate_signal
>>> drift = calculate_drift(snapshots, "NVDAB")
>>> generate_signal(drift["drift_pct"])
```

Cron (every 30 minutes, used in this build on a Contabo VPS):

```
*/30 * * * * CMC_MCP_API_KEY=<key> /bin/bash /path/to/BQuant/skills/bquant-weekend-drift/scripts/run_snapshot.sh >> /path/to/BQuant/data/snapshot.log 2>&1
```

---


---

## License

MIT.
