"""
main.py — Entry point for batch simulation runs.

Run this as a script, never from a notebook.
Edit the EXPRESSIONS list below with your alpha ideas,
then: python main.py

Settings are controlled via .env or config.py — not here.
"""

import os
import json
from auth import create_session
from simulate import batch_simulate
from results import fetch_all_recordsets
from config import build_alpha, BATCH_SIZE, QUOTA_FLOOR, RESULTS_OUTPUT_DIR

# ── Define your alpha expressions here ───────────────────────────────────────

EXPRESSIONS = [
    "ts_mean(close, 5) / ts_mean(close, 20)",
    "ts_delta(volume, 5)",
    "group_rank(ts_zscore(close, 21), 'subindustry')",
    # Add more expressions here...
]

# Optional per-expression setting overrides.
# If None, all expressions use DEFAULTS from config.py.
# Example: override decay and neutralization for a specific expression.
OVERRIDES = {
    "ts_delta(volume, 5)": {"decay": 0, "neutralization": "MARKET"},
}

# ── Which recordsets to fetch after simulation ────────────────────────────────

FETCH_RECORDSETS = ["pnl", "sharpe", "turnover", "yearly-stats"]

# ─────────────────────────────────────────────────────────────────────────────


def save_results(alpha_id: str, recordsets: dict):
    """Persist fetched recordsets to JSON files for later notebook analysis."""
    out_dir = os.path.join(RESULTS_OUTPUT_DIR, alpha_id)
    os.makedirs(out_dir, exist_ok=True)
    for name, df in recordsets.items():
        path = os.path.join(out_dir, f"{name}.json")
        df.to_json(path, orient="records", date_format="iso")
    print(f"  Results saved → {out_dir}/")


def main():
    print("=" * 50)
    print("  WorldQuant Brain — Batch Simulation Runner")
    print("=" * 50)

    # 1. Authenticate
    session = create_session()

    # 2. Build alpha config list
    alpha_list = [
        build_alpha(expr, overrides=OVERRIDES.get(expr))
        for expr in EXPRESSIONS
    ]
    print(f"\n{len(alpha_list)} expressions loaded.\n")

    # 3. Run batch simulation (cache-aware)
    run_results = batch_simulate(
        session,
        alpha_list,
        batch_size=BATCH_SIZE,
        stop_at_remaining=QUOTA_FLOOR,
    )

    # 4. Collect all successful alpha_ids (new + cached)
    all_pairs = run_results["simulated"] + run_results["cached"]

    if not all_pairs:
        print("\nNo alpha IDs to fetch results for. Check for errors above.")
        return

    # 5. Fetch and save results for each alpha
    print(f"\nFetching results for {len(all_pairs)} alphas...")
    for _, alpha_id in all_pairs:
        print(f"\n  Alpha: {alpha_id}")
        recordsets = fetch_all_recordsets(session, alpha_id, FETCH_RECORDSETS)
        save_results(alpha_id, recordsets)

    # 6. Write a run manifest so the notebook knows what was just simulated
    manifest_path = os.path.join(RESULTS_OUTPUT_DIR, "last_run.json")
    os.makedirs(RESULTS_OUTPUT_DIR, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(
            {
                "simulated": [aid for _, aid in run_results["simulated"]],
                "cached": [aid for _, aid in run_results["cached"]],
                "failed_count": len(run_results["failed"]),
            },
            f,
            indent=2,
        )
    print(f"\n✓ Run manifest saved → {manifest_path}")
    print("\nDone. Open notebooks/analysis.ipynb to explore results.")


if __name__ == "__main__":
    main()
