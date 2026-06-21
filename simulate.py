"""
simulate.py — Batch simulation engine for WQ Brain API.

Handles:
- Quota monitoring via response headers
- Chunked multi-simulation (max 10 per batch)
- Polling for completion
- Cache-aware deduplication
"""

from time import sleep
from typing import Optional
from cache import check_cache, add_to_cache

BASE_URL = "https://api.worldquantbrain.com"

# Safe default: 8 instead of 10 to avoid edge cases with the API limit
DEFAULT_BATCH_SIZE = 8


def _log_quota(headers: dict):
    remaining = headers.get("x-ratelimit-remaining", "?")
    limit = headers.get("x-ratelimit-limit", "?")
    reset = headers.get("x-ratelimit-reset", "?")
    print(f"  Quota: {remaining}/{limit} remaining (resets in {reset}s)")


def _poll_until_complete(session, progress_url: str) -> Optional[dict]:
    """
    Poll a simulation progress URL until it completes.
    Respects the Retry-After header from the server.

    Returns:
        Completed simulation response JSON, or None on failure.
    """
    while True:
        response = session.get(progress_url)
        retry_after = float(response.headers.get("Retry-After", 0))

        if retry_after == 0:
            data = response.json()
            status = data.get("status", "UNKNOWN")

            if status in ("ERROR", "FAIL", "TIMEOUT", "CANCELLED"):
                print(f"  ✗ Simulation ended with status: {status}")
                msg = data.get("message", "")
                if msg:
                    print(f"    Message: {msg}")
                return None

            return data

        progress = data.get("progress", "?") if hasattr(response, "json") else "?"
        print(f"  Simulating... progress={progress} | waiting {retry_after}s")
        sleep(retry_after)


def _submit_batch(session, batch: list) -> list[str]:
    """
    Submit a batch of 1–10 alpha configs and return completed alpha_ids.
    """
    payload = batch if len(batch) > 1 else batch[0]
    response = session.post(f"{BASE_URL}/simulations", json=payload)

    _log_quota(response.headers)

    if response.status_code != 201:
        print(f"  ✗ Batch submission failed [{response.status_code}]: {response.text}")
        return []

    progress_url = response.headers["Location"]
    result = _poll_until_complete(session, progress_url)

    if result is None:
        return []

    # Multi-sim returns children; single sim returns alpha directly
    children = result.get("children")
    if children:
        return [c for c in children if c]
    
    alpha_id = result.get("alpha")
    return [alpha_id] if alpha_id else []


def batch_simulate(
    session,
    alpha_list: list,
    batch_size: int = DEFAULT_BATCH_SIZE,
    stop_at_remaining: int = 50,
) -> dict:
    """
    Main entry point for batch simulation.

    Args:
        session:             Authenticated requests.Session
        alpha_list:          List of alpha config dicts
        batch_size:          Number of alphas per API call (max 10, default 8)
        stop_at_remaining:   Halt if quota drops below this threshold

    Returns:
        dict with keys:
            "simulated"  -> list of (alpha_dict, alpha_id) for newly simulated
            "cached"     -> list of (alpha_dict, alpha_id) from cache
            "failed"     -> list of alpha_dicts that errored
    """
    if batch_size > 10:
        raise ValueError("batch_size cannot exceed 10 — API hard limit.")

    new_alphas, cached_results = [], []

    for alpha in alpha_list:
        cached_id = check_cache(alpha)
        if cached_id:
            cached_results.append((alpha, cached_id))
        else:
            new_alphas.append(alpha)

    print(f"✓ Deduplication complete: {len(cached_results)} cached | {len(new_alphas)} new")

    simulated_results, failed = [], []

    for i in range(0, len(new_alphas), batch_size):
        chunk = new_alphas[i : i + batch_size]
        chunk_num = (i // batch_size) + 1
        total_chunks = -(-len(new_alphas) // batch_size)  # ceiling division
        print(f"\nBatch {chunk_num}/{total_chunks} ({len(chunk)} alphas)...")

        alpha_ids = _submit_batch(session, chunk)

        if not alpha_ids:
            failed.extend(chunk)
            continue

        for alpha_dict, alpha_id in zip(chunk, alpha_ids):
            add_to_cache(alpha_dict, alpha_id)
            simulated_results.append((alpha_dict, alpha_id))
            print(f"  ✓ {alpha_id}")

    print(f"\n── Summary ──────────────────────────────")
    print(f"  Simulated : {len(simulated_results)}")
    print(f"  From cache: {len(cached_results)}")
    print(f"  Failed    : {len(failed)}")

    return {
        "simulated": simulated_results,
        "cached": cached_results,
        "failed": failed,
    }
