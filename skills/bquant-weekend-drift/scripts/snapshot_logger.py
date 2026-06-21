"""
Append a price snapshot for all bStock tokens to the top-level data/weekend_snapshots.json.
Driven by the CMC Skill Hub MCP tool (see SKILL.md). Run on cron every 30-60 min.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure scripts/ is on path when loaded via importlib from a parent directory
_scripts_dir = str(Path(__file__).parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from tokens import LIVE_TOKENS  # noqa: E402

# Resolve top-level data/ regardless of where this script lives:
# scripts/ -> bquant-weekend-drift/ -> skills/ -> project root
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = _PROJECT_ROOT / "data"
SNAPSHOT_FILE = DATA_DIR / "weekend_snapshots.json"


def log_snapshot(prices: dict) -> dict:
    """
    Append one snapshot entry to weekend_snapshots.json.

    Args:
        prices: {token: price_usd} for one or more TOKENS.

    Returns:
        The entry that was written.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    existing = []
    if SNAPSHOT_FILE.exists():
        with open(SNAPSHOT_FILE) as f:
            existing = json.load(f)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prices": {t: float(prices[t]) for t in LIVE_TOKENS if t in prices},
    }

    existing.append(entry)

    with open(SNAPSHOT_FILE, "w") as f:
        json.dump(existing, f, indent=2)

    print(f"[snapshot_logger] Logged {len(entry['prices'])} tokens @ {entry['timestamp']}")
    return entry


if __name__ == "__main__":
    # CLI: snapshot_logger.py NVDAB=135.20,TSLAB=242.10,...
    if len(sys.argv) < 2:
        print("Usage: snapshot_logger.py TOKEN=PRICE,TOKEN=PRICE,...")
        sys.exit(1)
    raw = dict(pair.split("=") for pair in sys.argv[1].split(","))
    log_snapshot(raw)
