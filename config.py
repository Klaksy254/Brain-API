"""
config.py — Centralised simulation settings.

All tuneable parameters live here. Import this in main.py and
the notebook so there is exactly ONE place to change settings.

Copy .env.example to .env and fill in your values.
Never commit .env to version control.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Simulation defaults ───────────────────────────────────────────────────────

DEFAULTS = {
    "type": "REGULAR",
    "settings": {
        "instrumentType": os.getenv("WQ_INSTRUMENT_TYPE", "EQUITY"),
        "region":         os.getenv("WQ_REGION", "USA"),
        "universe":       os.getenv("WQ_UNIVERSE", "TOP3000"),
        "delay":          int(os.getenv("WQ_DELAY", 1)),
        "decay":          int(os.getenv("WQ_DECAY", 15)),
        "neutralization": os.getenv("WQ_NEUTRALIZATION", "SUBINDUSTRY"),
        "truncation":     float(os.getenv("WQ_TRUNCATION", 0.08)),
        "pasteurization": os.getenv("WQ_PASTEURIZATION", "ON"),
        "testPeriod":     os.getenv("WQ_TEST_PERIOD", "P1Y6M"),
        "unitHandling":   os.getenv("WQ_UNIT_HANDLING", "VERIFY"),
        "nanHandling":    os.getenv("WQ_NAN_HANDLING", "OFF"),
        "language":       os.getenv("WQ_LANGUAGE", "FASTEXPR"),
        "visualization":  False,
    },
}

# ── Batch runner settings ─────────────────────────────────────────────────────

# Max alphas per API call. Hard API limit is 10; keep at 8 for safety.
BATCH_SIZE = int(os.getenv("WQ_BATCH_SIZE", 8))

# Stop submitting if remaining daily quota drops to this threshold.
QUOTA_FLOOR = int(os.getenv("WQ_QUOTA_FLOOR", 50))

# ── Paths ─────────────────────────────────────────────────────────────────────

CACHE_PATH        = os.getenv("WQ_CACHE_PATH", "simulation_cache.parquet")
CREDENTIALS_PATH  = os.getenv("WQ_CREDENTIALS_PATH", "~/.brain_credentials")
RESULTS_OUTPUT_DIR = os.getenv("WQ_RESULTS_DIR", "results/")


def build_alpha(expression: str, overrides: dict = None) -> dict:
    """
    Build a simulation payload from the default settings.

    Args:
        expression: The alpha expression string (FASTEXPR or Python)
        overrides:  Optional dict to override specific settings fields

    Returns:
        Complete simulation config dict ready to POST to /simulations

    Example:
        alpha = build_alpha("ts_mean(close, 5) / ts_mean(close, 20)")
        alpha = build_alpha("close", overrides={"decay": 0, "neutralization": "MARKET"})
    """
    import copy
    config = copy.deepcopy(DEFAULTS)
    config["regular"] = expression

    if overrides:
        config["settings"].update(overrides)

    return config
