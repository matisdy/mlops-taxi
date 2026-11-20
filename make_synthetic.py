"""Synthetic hourly pickups in the exact format of data/features.parquet."""
from pathlib import Path

import numpy as np
import pandas as pd

START = pd.Timestamp("2020-01-08")  # first hour kept (as in features.parquet)
WARMUP_DAYS = 7  # extra days simulated before START so no lag is missing
LEVELS = {132: 120.0, 161: 80.0, 237: 100.0}  # mean pickups per hour, per zone
DEFAULT_LEVEL = 60.0

# Hourly profile: quiet at night, peaks in the morning and in the evening.
HOUR_PROFILE = np.array(
    [0.3, 0.2, 0.15, 0.1, 0.1, 0.2, 0.5, 1.0, 1.5, 1.2, 1.0, 1.0,
     1.1, 1.0, 1.0, 1.1, 1.3, 1.6, 1.8, 1.5, 1.2, 1.0, 0.7, 0.5]
)


def make_synthetic(days=21, zones=(132, 161, 237), seed=0) -> pd.DataFrame:
    """Return a features.parquet-like frame: one row per zone and hour.

    y ~ Poisson(zone level x hourly profile). Lags are computed with shift on
    the full hourly grid (7 warm-up days included), then the warm-up is dropped.
    The first 14 days are "train", the following ones "valid".
    """
    rng = np.random.default_rng(seed)
    grid = pd.date_range(START - pd.Timedelta(days=WARMUP_DAYS),
                         START + pd.Timedelta(days=days), freq="h", inclusive="left")
    parts = []
    for zone in zones:
        df = pd.DataFrame({"ts": grid, "zone": zone})
        mean = LEVELS.get(zone, DEFAULT_LEVEL) * HOUR_PROFILE[grid.hour]
        df["y"] = rng.poisson(mean).astype("float64")
        for name, hours in [("lag_1h", 1), ("lag_24h", 24), ("lag_168h", 168)]:
            df[name] = df["y"].shift(hours)
        parts.append(df)
    df = pd.concat(parts)
    df = df[df["ts"] >= START]
    df["zone"] = df["zone"].astype("int64")
    df["hour"] = df["ts"].dt.hour.astype("int64")
    df["dow"] = df["ts"].dt.day_of_week.astype("int64")
    df["split"] = np.where(df["ts"] < START + pd.Timedelta(days=14), "train", "valid")
    cols = ["ts", "zone", "hour", "dow", "lag_1h", "lag_24h", "lag_168h", "y", "split"]
    return df[cols].sort_values(["ts", "zone"]).reset_index(drop=True)


if __name__ == "__main__":
    df = make_synthetic()
    Path("data").mkdir(exist_ok=True)
    df.to_parquet("data/synthetic.parquet", index=False)
    print(f"data/synthetic.parquet: {len(df)} rows")
    print("columns:", list(df.columns))
    print(df["split"].value_counts().to_string())
