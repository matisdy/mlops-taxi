"""Replay a period against the running API and write the ground truth, like L4 traffic.py (spec section 9).
Usage: uv run python replay.py --start 2020-02-17 --end 2020-02-29 [--hours-per-second 10] [--data PATH] [--url URL]
"""
import argparse
import csv
import os
import time
from pathlib import Path

import httpx
import pandas as pd
import yaml

TRUTH = Path("data/truth.csv")  # read back by check_and_retrain.py (task 5.2)
COLUMNS = ["ts", "zone", "hour", "dow", "lag_1h", "lag_24h", "lag_168h", "y", "prediction", "model_version"]


def one(client: httpx.Client, row: dict, out: csv.writer, stats: dict) -> None:
    """POST one zone and hour to the API; on a 200, append the row and the answer to truth.csv."""
    # spec section 7: exactly these five fields, the API answers 422 to any other one
    body = {
        "zone": int(row["zone"]),
        "ts": row["ts"].isoformat(),
        "lag_1h": float(row["lag_1h"]),
        "lag_24h": float(row["lag_24h"]),
        "lag_168h": float(row["lag_168h"]),
    }
    # L4 traffic.py l. 42-50: a 200 goes to the CSV, any other answer or an HTTP error is an error
    try:
        r = client.post("/v1/predict", json=body)
        stats["ok" if r.status_code == 200 else "err"] += 1
        if r.status_code == 200:
            answer = r.json()
            # Python floats are written 112.0, never 112: task 5.2 retrains on this file
            out.writerow([body["ts"], body["zone"], int(row["hour"]), int(row["dow"]), body["lag_1h"],
                          body["lag_24h"], body["lag_168h"], float(row["y"]), float(answer["prediction"]),
                          answer["model_version"]])
        elif stats["err"] == 1:
            print(f"  first error: {r.status_code} {r.text[:200]}")  # once, so that a 422 explains itself
    except httpx.HTTPError as e:
        stats["err"] += 1
        if stats["err"] == 1:
            print(f"  first error: {e!r}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Replay a period against the running API, write data/truth.csv.")
    ap.add_argument("--start", required=True, help="first day, YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="last day, included, YYYY-MM-DD")
    ap.add_argument("--hours-per-second", type=float, default=10,
                    help="simulated hours per second (default: %(default)s)")
    # params.yaml read with yaml, not train.load_params(): importing train.py would load mlflow
    ap.add_argument("--data", default=yaml.safe_load(open("params.yaml"))["data"]["features"],
                    help="features Parquet file (default: %(default)s)")
    ap.add_argument("--url", default=os.getenv("API_URL", "http://127.0.0.1:8000"),  # spec section 1
                    help="API URL (default: %(default)s)")
    a = ap.parse_args()

    df = pd.read_parquet(a.data)
    # days included: from start 00:00 to end 23:00
    start, end = pd.Timestamp(a.start), pd.Timestamp(a.end) + pd.Timedelta(days=1)
    df = df[(df["ts"] >= start) & (df["ts"] < end)]

    stats = {"ok": 0, "err": 0}
    TRUTH.parent.mkdir(parents=True, exist_ok=True)
    new = not TRUTH.exists()
    # L4 traffic.py l. 75-80: append to the CSV, header only for a new file, one client for every request
    with open(TRUTH, "a", newline="") as f:
        out = csv.writer(f)
        if new:
            out.writerow(COLUMNS)
        with httpx.Client(base_url=a.url, timeout=10) as client:
            print(f"{a.start} to {a.end}: {df['ts'].nunique()} hours x {df['zone'].nunique()} zones, "
                  f"{a.hours_per_second:g} hours/s, {a.url}, Ctrl+C to stop")
            # L4 traffic.py l. 85-92: a simulated hour lasts 1 / hours_per_second s (no sleep if the API
            # is slow), progress every 24 simulated hours
            t = time.time()
            for i, (ts, hour) in enumerate(df.groupby("ts"), start=1):  # groupby sorts the hours
                for row in hour.to_dict("records"):
                    one(client, row, out, stats)
                t += 1 / a.hours_per_second
                time.sleep(max(0, t - time.time()))
                if i % 24 == 0:
                    print(f"  {ts:%Y-%m-%d} sent {stats['ok'] + stats['err']}, ok {stats['ok']}, errors {stats['err']}")
    print(f"done: ok {stats['ok']}, errors {stats['err']}, rows appended to {TRUTH}")


if __name__ == "__main__":
    # L4 traffic.py l. 97-101; the rows already written stay in truth.csv
    try:
        main()
    except KeyboardInterrupt:
        print("stopped")
