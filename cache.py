"""
cache.py — Local hash-based deduplication cache.

Prevents re-simulating identical alpha configurations,
protecting your daily simulation quota.

Cache is stored as a parquet file for efficient lookup.
"""

import os
import hashlib
import json
import pandas as pd
from datetime import datetime, timezone
from typing import Optional

CACHE_PATH = "simulation_cache.parquet"
_CACHE_COLUMNS = ["alpha_hashed", "alpha_id", "date_created"]


def _ensure_cache():
    if not os.path.exists(CACHE_PATH):
        pd.DataFrame(columns=_CACHE_COLUMNS).to_parquet(CACHE_PATH, index=False)
        print(f"✓ Simulation cache created at: {CACHE_PATH}")


def hash_alpha(alpha_dict: dict) -> str:
    """
    Deterministically hash an alpha configuration dictionary.
    Keys are sorted so insertion order doesn't affect the hash.
    """
    serialized = json.dumps(alpha_dict, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def check_cache(alpha_dict: dict) -> Optional[str]:
    """
    Check if an alpha config was already simulated.

    Returns:
        alpha_id (str) if found in cache, None otherwise.
    """
    _ensure_cache()
    df = pd.read_parquet(CACHE_PATH)
    matches = df[df["alpha_hashed"] == hash_alpha(alpha_dict)]
    if len(matches) == 0:
        return None
    return matches.iloc[0]["alpha_id"]


def add_to_cache(alpha_dict: dict, alpha_id: str):
    """
    Record a newly simulated alpha in the cache.
    """
    _ensure_cache()
    df = pd.read_parquet(CACHE_PATH)
    new_row = pd.DataFrame([{
        "alpha_hashed": hash_alpha(alpha_dict),
        "alpha_id": alpha_id,
        "date_created": datetime.now(timezone.utc),
    }])
    pd.concat([df, new_row], ignore_index=True).to_parquet(CACHE_PATH, index=False)


def cache_stats() -> dict:
    """
    Return a summary of the current cache state.
    Useful for monitoring in the analysis notebook.
    """
    _ensure_cache()
    df = pd.read_parquet(CACHE_PATH)
    if df.empty:
        return {"total": 0, "oldest": None, "newest": None}
    return {
        "total": len(df),
        "oldest": df["date_created"].min(),
        "newest": df["date_created"].max(),
    }


def clear_cache():
    """
    Wipe the cache. Use with caution — this cannot be undone.
    """
    confirm = input("This will delete all cached simulations. Type 'yes' to confirm: ")
    if confirm.strip().lower() == "yes":
        os.remove(CACHE_PATH)
        print("Cache cleared.")
    else:
        print("Aborted.")
