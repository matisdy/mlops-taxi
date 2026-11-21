"""Build data/features.parquet and data/zones.json from the raw TLC files (spec section 4).
Usage: uv run python build_dataset.py
"""
import json
from pathlib import Path

import pandas as pd
import yaml


def build_features(trips: pd.DataFrame, params: dict, zones: list[int] | None = None) -> tuple[pd.DataFrame, list[int]]:
    """One row per zone and hour, in the format of data/features.parquet (spec section 4).

    trips: tpep_pickup_datetime and PULocationID, the other columns are ignored. Without zones, take
    the n_zones PULocationID with the most trips in the train range, ties going to the smallest id.
    Returns (features, zones), zones as a sorted list of int.
    """
    months = params["data"]["months"]
    start = pd.Timestamp(months[0])  # first day of the first month, 00:00
    end = pd.Period(months[-1], freq="M").end_time.floor("h")  # last day of the last month, 23:00
    hours = pd.date_range(start, end, freq="h")  # no time zone: New York local time, no conversion

    # Hour of each pickup, at the resolution of the grid whatever the input one ([s], [us], [ns]),
    # so that the reindex below matches. Drops the odd dates of the files (2003 to 2021).
    ts = trips["tpep_pickup_datetime"].dt.floor("h").dt.as_unit(hours.unit)
    trips = pd.DataFrame({"zone": trips["PULocationID"], "ts": ts})
    trips = trips[trips["ts"].between(start, end)]
    if not zones:
        train = trips[trips["ts"].between(*params["split"]["train"])]
        # ids in ascending order first, so that nlargest keeps the smallest id on ties
        zones = train["zone"].value_counts().sort_index().nlargest(params["data"]["n_zones"]).index
    zones = sorted(int(zone) for zone in zones)

    # Trips per (zone, hour) with groupby (L4 join_labels.py l. 19), then the full grid of
    # zones x hours, sorted by zone then ts: an hour without trips is 0.
    grid = pd.MultiIndex.from_product([zones, hours], names=["zone", "ts"])
    y = trips.groupby(["zone", "ts"]).size().reindex(grid, fill_value=0).astype("float64")
    df = y.rename("y").reset_index()

    # EC-1, the course has no lagged variables: shift within each zone, on the full grid,
    # before any row is dropped.
    for name, n in [("lag_1h", 1), ("lag_24h", 24), ("lag_168h", 168)]:
        df[name] = df.groupby("zone")["y"].shift(n)
    df["hour"] = df["ts"].dt.hour.astype("int64")
    df["dow"] = df["ts"].dt.day_of_week.astype("int64")  # Monday = 0 (dt.dayofweek is deprecated in pandas 3)

    # EC-3: split by dates, never at random as L1 train.py l. 37 does. The hours outside the
    # three ranges (the first week, only there for the lags) are dropped.
    df["split"] = ""
    for name in ("train", "valid", "replay"):
        df.loc[df["ts"].between(*params["split"][name]), "split"] = name
    df = df[df["split"] != ""]
    cols = ["ts", "zone", "hour", "dow", "lag_1h", "lag_24h", "lag_168h", "y", "split"]
    return df[cols].reset_index(drop=True), zones


if __name__ == "__main__":
    params = yaml.safe_load(open("params.yaml"))  # L1 train.py l. 26
    data = params["data"]
    # The raw files of task 1.1, two columns only (spec section 4)
    paths = [Path(data["raw_dir"]) / f"yellow_tripdata_{month}.parquet" for month in data["months"]]
    trips = pd.concat(
        [pd.read_parquet(path, columns=["tpep_pickup_datetime", "PULocationID"]) for path in paths],
        ignore_index=True,
    )
    df, zones = build_features(trips, params)
    # Data written by a script, then versioned with dvc add (L1 gen_data.py l. 41-46)
    df.to_parquet(data["features"], index=False)
    with open(data["zones"], "w") as f:
        json.dump(zones, f)
    print(f"{data['features']}: {len(df)} rows")
    print("columns:", list(df.columns))
    print(df["split"].value_counts().to_string())
    print(f"{data['zones']}: {zones}")
