"""
BQuant Weekend Drift Engine.
All functions accept and return plain JSON-serializable dicts. No external state.
"""

from __future__ import annotations
import sys
from pathlib import Path

# Ensure scripts/ is on path when loaded via importlib from a parent directory
_scripts_dir = str(Path(__file__).parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from tokens import LIVE_TOKENS, BSTOCKS  # noqa: E402

# Drift thresholds from AGENTS.md — do not change without explicit sign-off
_SIGNAL_THRESHOLD = 0.015   # |drift| > 1.5% → LONG or SHORT
_CONVERGE_THRESHOLD = 0.003  # |drift| < 0.3% → CONVERGED / exit


def calculate_drift(snapshots: list, token: str) -> dict:
    """
    Calculate weekend drift for one token across a list of price snapshots.

    Args:
        snapshots: List of {"timestamp": str, "prices": {token: float}} as written
                   by snapshot_logger.py.
        token:     Ticker string, e.g. "NVDAB".

    Returns:
        {
          "token":              str,
          "anchor_price":       float,
          "anchor_timestamp":   str,
          "current_price":      float,
          "current_timestamp":  str,
          "drift_pct":          float,   # (current - anchor) / anchor, fractional
          "snapshot_count":     int,
          "ok":                 bool,
          "error":              str | None,
        }
    """
    relevant = [s for s in snapshots if token in s.get("prices", {})]

    if len(relevant) < 2:
        return {
            "token": token,
            "ok": False,
            "error": f"Need ≥2 snapshots containing {token}; have {len(relevant)}.",
        }

    t0 = relevant[0]
    t_now = relevant[-1]
    anchor_price = float(t0["prices"][token])
    current_price = float(t_now["prices"][token])

    if anchor_price == 0:
        return {"token": token, "ok": False, "error": "Anchor price is zero."}

    drift_pct = (current_price - anchor_price) / anchor_price

    return {
        "token": token,
        "anchor_price": anchor_price,
        "anchor_timestamp": t0["timestamp"],
        "current_price": current_price,
        "current_timestamp": t_now["timestamp"],
        "drift_pct": round(drift_pct, 6),
        "snapshot_count": len(relevant),
        "ok": True,
        "error": None,
    }


def generate_signal(drift_pct: float) -> dict:
    """
    Map a drift percentage to a mean-reversion trading signal.

    Signal logic (from AGENTS.md, do not change without sign-off):
      |drift| > 1.5%  →  LONG/SHORT; direction is opposite to drift (reversion bet)
      |drift| < 0.3%  →  CONVERGED (exit)
      else            →  FLAT

    Args:
        drift_pct: Fractional drift, e.g. 0.025 for +2.5%.

    Returns:
        {
          "signal":     "LONG" | "SHORT" | "FLAT" | "CONVERGED",
          "confidence": int,   # 0–100
          "reasoning":  str,
        }
    """
    abs_drift = abs(drift_pct)
    pct_display = drift_pct * 100

    if abs_drift < _CONVERGE_THRESHOLD:
        return {
            "signal": "CONVERGED",
            "confidence": 90,
            "reasoning": (
                f"Drift {pct_display:+.2f}% is below the convergence threshold "
                f"({_CONVERGE_THRESHOLD * 100:.1f}%); position should be exited or not opened."
            ),
        }

    if abs_drift > _SIGNAL_THRESHOLD:
        # Reversion bet: if price drifted UP, we expect it to fall back → SHORT.
        # If price drifted DOWN, we expect it to recover → LONG.
        direction = "SHORT" if drift_pct > 0 else "LONG"
        # Confidence: 60 at the threshold, scaling to 85 at 3× threshold, capped at 85.
        excess = (abs_drift - _SIGNAL_THRESHOLD) / (_SIGNAL_THRESHOLD * 2)
        confidence = round(60 + 25 * min(excess, 1.0))
        return {
            "signal": direction,
            "confidence": confidence,
            "reasoning": (
                f"Drift {pct_display:+.2f}% exceeds the ±{_SIGNAL_THRESHOLD * 100:.1f}% threshold; "
                f"mean-reversion to NYSE/Nasdaq anchor expected — signal {direction}."
            ),
        }

    return {
        "signal": "FLAT",
        "confidence": 50,
        "reasoning": (
            f"Drift {pct_display:+.2f}% falls between the convergence "
            f"({_CONVERGE_THRESHOLD * 100:.1f}%) and signal ({_SIGNAL_THRESHOLD * 100:.1f}%) "
            "thresholds; insufficient edge to act."
        ),
    }
