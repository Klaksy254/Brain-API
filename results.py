"""
results.py — Fetch and parse alpha simulation results.

Supports all recordsets documented in the WQ Brain API:
  pnl, sharpe, turnover, daily-pnl, yearly-stats,
  coverage, coverage-by-industry, coverage-by-sector,
  pnl-by-sector, pnl-by-industry, pnl-by-capitalization,
  sharpe-by-sector, sharpe-by-industry, sharpe-by-capitalization,
  average-size-by-sector, average-size-by-industry,
  average-size-by-capitalization,
  average-value-by-sector, average-value-by-industry
"""

from time import sleep
import pandas as pd
from typing import Optional

BASE_URL = "https://api.worldquantbrain.com"

# All recordsets available per the API docs
ALL_RECORDSETS = [
    "pnl",
    "sharpe",
    "turnover",
    "daily-pnl",
    "yearly-stats",
    "coverage",
    "coverage-by-industry",
    "coverage-by-sector",
    "pnl-by-sector",
    "pnl-by-industry",
    "pnl-by-capitalization",
    "sharpe-by-sector",
    "sharpe-by-industry",
    "sharpe-by-capitalization",
    "average-size-by-sector",
    "average-size-by-industry",
    "average-size-by-capitalization",
    "average-value-by-sector",
    "average-value-by-industry",
]


def _recordset_to_dataframe(data: dict) -> pd.DataFrame:
    """
    Parse the WQ Brain recordset format into a pandas DataFrame.
    The API returns schema + records as parallel arrays.
    """
    schema = data.get("schema", {})
    properties = schema.get("properties", [])
    records = data.get("records", [])

    columns = [p["name"] for p in properties]
    df = pd.DataFrame(records, columns=columns)

    # Parse date columns
    date_cols = [p["name"] for p in properties if p.get("type") == "date"]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col])

    return df


def _fetch_recordset(
    session, alpha_id: str, recordset: str
) -> Optional[pd.DataFrame]:
    """
    Fetch a single recordset for an alpha, polling until ready.
    """
    url = f"{BASE_URL}/alphas/{alpha_id}/recordsets/{recordset}"

    while True:
        response = session.get(url)

        if response.status_code == 404:
            print(f"  Recordset '{recordset}' not found for alpha {alpha_id}")
            return None

        retry_after = float(response.headers.get("Retry-After", 0))
        if retry_after == 0:
            return _recordset_to_dataframe(response.json())

        sleep(retry_after)


def fetch_alpha_details(session, alpha_id: str) -> dict:
    """
    Fetch the full alpha object including settings and expression.
    """
    response = session.get(f"{BASE_URL}/alphas/{alpha_id}")
    if response.status_code != 200:
        raise ValueError(f"Could not fetch alpha {alpha_id}: {response.status_code}")
    return response.json()


def fetch_pnl(session, alpha_id: str) -> Optional[pd.DataFrame]:
    """Fetch cumulative PnL timeseries."""
    return _fetch_recordset(session, alpha_id, "pnl")


def fetch_sharpe(session, alpha_id: str) -> Optional[pd.DataFrame]:
    """Fetch Sharpe ratio timeseries."""
    return _fetch_recordset(session, alpha_id, "sharpe")


def fetch_turnover(session, alpha_id: str) -> Optional[pd.DataFrame]:
    """Fetch turnover timeseries."""
    return _fetch_recordset(session, alpha_id, "turnover")


def fetch_yearly_stats(session, alpha_id: str) -> Optional[pd.DataFrame]:
    """Fetch per-year performance breakdown."""
    return _fetch_recordset(session, alpha_id, "yearly-stats")


def fetch_all_recordsets(
    session, alpha_id: str, recordsets: list = None
) -> dict[str, pd.DataFrame]:
    """
    Fetch multiple recordsets for a single alpha.

    Args:
        session:    Authenticated session
        alpha_id:   Alpha ID string
        recordsets: List of recordset names. Defaults to the core set
                    (pnl, sharpe, turnover, yearly-stats).

    Returns:
        Dict mapping recordset name -> DataFrame
    """
    if recordsets is None:
        recordsets = ["pnl", "sharpe", "turnover", "yearly-stats"]

    results = {}
    for rs in recordsets:
        print(f"  Fetching {rs}...")
        df = _fetch_recordset(session, alpha_id, rs)
        if df is not None:
            results[rs] = df

    return results


def compare_alphas(
    session, alpha_ids: list, metric: str = "pnl"
) -> pd.DataFrame:
    """
    Fetch the same metric for multiple alphas and merge into a single
    DataFrame for side-by-side comparison. Ideal for notebook charting.

    Args:
        session:   Authenticated session
        alpha_ids: List of alpha ID strings
        metric:    Recordset name to compare (default: 'pnl')

    Returns:
        Wide-format DataFrame with date index and one column per alpha.
    """
    frames = {}
    for alpha_id in alpha_ids:
        df = _fetch_recordset(session, alpha_id, metric)
        if df is not None and "date" in df.columns:
            col = metric if metric not in df.columns else metric
            # Use the first non-date numeric column
            value_cols = [c for c in df.columns if c != "date"]
            if value_cols:
                frames[alpha_id] = df.set_index("date")[value_cols[0]]

    if not frames:
        return pd.DataFrame()

    combined = pd.DataFrame(frames)
    combined.index.name = "date"
    return combined
