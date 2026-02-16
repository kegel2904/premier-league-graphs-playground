"""
FPL ETL Pipeline
Extracts data from vaastav/Fantasy-Premier-League GitHub dataset
Transforms into price-per-point metrics
Outputs a clean parquet file for the dashboard
"""

import pandas as pd
import os

# ── Config ────────────────────────────────────────────────────────────────────
SEASON = "2024-25"
BASE_URL = f"https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/{SEASON}/gws/merged_gw.csv"
OUTPUT_DIR = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "fpl_price_per_point.csv")


def extract(url: str) -> pd.DataFrame:
    """Download the merged gameweek CSV from GitHub."""
    print(f"[EXTRACT] Downloading {SEASON} data from GitHub...")
    df = pd.read_csv(url)
    print(f"[EXTRACT] {len(df):,} rows, {df['name'].nunique()} unique players, GW1–GW{df['GW'].max()}")
    return df


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate 3 price-per-point metrics per player:
      1. total_pts_per_avg_price  → Total Points / Average price across season
      2. total_pts_per_gw1_price  → Total Points / Price at GW1
      3. total_pts_per_gw38_price → Total Points / Price at GW38
    
    NOTE: 'value' column is in tenths (e.g. 65 = £6.5m). We convert to £m.
    """
    print("[TRANSFORM] Starting transformations...")

    df = df.copy()

    # Convert value to £m
    df["price_m"] = df["value"] / 10.0

    # ── Per-player aggregations ───────────────────────────────────────────────

    # Total points across the season
    total_pts = (
        df.groupby("name")["total_points"]
        .sum()
        .reset_index()
        .rename(columns={"total_points": "total_pts"})
    )

    # Average price across all GWs played
    avg_price = (
        df.groupby("name")["price_m"]
        .mean()
        .reset_index()
        .rename(columns={"price_m": "avg_price_m"})
    )

    # Price at GW1 (earliest GW the player appeared)
    gw1_price = (
        df.sort_values("GW")
        .groupby("name")
        .first()
        .reset_index()[["name", "price_m", "GW", "position", "team"]]
        .rename(columns={"price_m": "gw1_price_m", "GW": "first_gw"})
    )

    # Price at GW38 (or last GW the player appeared)
    gw_last_price = (
        df.sort_values("GW")
        .groupby("name")
        .last()
        .reset_index()[["name", "price_m", "GW"]]
        .rename(columns={"price_m": "gw_last_price_m", "GW": "last_gw"})
    )

    # GWs played (non-zero minute appearances)
    gws_played = (
        df[df["minutes"] > 0]
        .groupby("name")["GW"]
        .nunique()
        .reset_index()
        .rename(columns={"GW": "gws_played"})
    )

    # ── Merge all together ────────────────────────────────────────────────────
    result = (
        total_pts
        .merge(avg_price, on="name")
        .merge(gw1_price, on="name")
        .merge(gw_last_price, on="name")
        .merge(gws_played, on="name", how="left")
    )

    # ── The 3 core calculations ───────────────────────────────────────────────
    result["pts_per_avg_price"] = (result["total_pts"] / result["avg_price_m"]).round(2)
    result["pts_per_gw1_price"] = (result["total_pts"] / result["gw1_price_m"]).round(2)
    result["pts_per_gw_last_price"] = (result["total_pts"] / result["gw_last_price_m"]).round(2)

    # Price change across season
    result["price_change_m"] = (result["gw_last_price_m"] - result["gw1_price_m"]).round(1)

    # Clean up
    result = result[result["gws_played"] >= 5]  # Filter out squad fillers
    result = result.sort_values("pts_per_avg_price", ascending=False).reset_index(drop=True)

    print(f"[TRANSFORM] {len(result)} players retained (≥5 GWs played)")
    return result


def load(df: pd.DataFrame, output_file: str):
    """Save transformed data to CSV."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df.to_csv(output_file, index=False)
    print(f"[LOAD] Saved to {output_file}")


def run():
    raw = extract(BASE_URL)
    transformed = transform(raw)
    load(transformed, OUTPUT_FILE)
    print("\n✅ ETL complete! Preview:")
    print(transformed[["name", "team", "position", "total_pts",
                         "gw1_price_m", "gw_last_price_m",
                         "pts_per_gw1_price", "pts_per_gw_last_price",
                         "pts_per_avg_price"]].head(10).to_string(index=False))
    return transformed


if __name__ == "__main__":
    run()