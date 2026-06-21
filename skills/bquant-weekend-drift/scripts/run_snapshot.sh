#!/usr/bin/env bash
# run_snapshot.sh — fetch live bStock prices from CMC REST API and log a snapshot.
# Resolves all paths relative to this file's location; safe to call from any cwd.
#
# Key: CMC_MCP_API_KEY — the same key used for CMC Skill Hub MCP also works for
# the REST API. Loaded automatically from .env (project parent dir) if not already
# exported; export it in the environment or crontab to override the .env value.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load CMC_MCP_API_KEY from .env if not already in environment.
# .env lives one level above the BQuant project root:
#   scripts/ → bquant-weekend-drift/ → skills/ → BQuant/ → <parent>/.env
# Compute ENV_FILE unconditionally so the error message can show the exact path tried.
ENV_FILE="$(cd "${SCRIPT_DIR}/../../../.." && pwd)/.env"

if [[ -z "${CMC_MCP_API_KEY:-}" ]]; then
    if [[ -f "${ENV_FILE}" ]]; then
        # shellcheck source=/dev/null
        source "${ENV_FILE}"
    fi
fi

if [[ -z "${CMC_MCP_API_KEY:-}" ]]; then
    echo "[run_snapshot] ERROR: CMC_MCP_API_KEY is not set." >&2
    echo "  Looked for .env at: ${ENV_FILE}" >&2
    echo "  File found there:   $(test -f "${ENV_FILE}" && echo yes || echo no)" >&2
    echo "  Fix: export CMC_MCP_API_KEY=<key> before running, or place it in the file above." >&2
    exit 1
fi

python3 - <<PYEOF
import json, os, sys, urllib.request, urllib.error

# Add scripts/ to path so tokens.py and snapshot_logger.py are importable directly.
# This is the workaround for the hyphenated directory name (bquant-weekend-drift)
# that prevents normal package imports.
sys.path.insert(0, "${SCRIPT_DIR}")

from tokens import LIVE_TOKENS
from snapshot_logger import log_snapshot

api_key = os.environ["CMC_MCP_API_KEY"]
symbols = ",".join(LIVE_TOKENS)
url = (
    "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    f"?symbol={symbols}&convert=USD"
)

req = urllib.request.Request(url, headers={"X-CMC_PRO_API_KEY": api_key})

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"[run_snapshot] CMC HTTP {e.code}: {body}", file=sys.stderr)
    sys.exit(1)
except urllib.error.URLError as e:
    print(f"[run_snapshot] CMC network error: {e.reason}", file=sys.stderr)
    sys.exit(1)

if data.get("status", {}).get("error_code", 0) != 0:
    print(f"[run_snapshot] CMC API error: {data['status']['error_message']}", file=sys.stderr)
    sys.exit(1)

prices = {}
missing = []
for token in LIVE_TOKENS:
    entry = data["data"].get(token)
    if entry:
        prices[token] = entry["quote"]["USD"]["price"]
    else:
        missing.append(token)

if missing:
    print(f"[run_snapshot] WARNING: no CMC data for {missing} — logging partial snapshot", file=sys.stderr)

if not prices:
    print("[run_snapshot] ERROR: zero prices returned from CMC — aborting, not logging", file=sys.stderr)
    sys.exit(1)

log_snapshot(prices)
PYEOF
