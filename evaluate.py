"""MAE per week of the model behind an alias, on the valid and replay rows ("Does it hurt?", S5 p. 22).
Usage: uv run python evaluate.py [alias] [--data data/synthetic.parquet]   (default alias: production)
"""
import argparse
import os
from pathlib import Path

# L1 score.py l. 5-6: keep the terminal clean
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
os.environ.setdefault("MLFLOW_ENABLE_ARTIFACTS_PROGRESS_BAR", "false")

import mlflow
import pandas as pd
from mlflow import MlflowClient

from train import baseline_mae, load_params, mae

NAME = os.getenv("MODEL_NAME", "taxi-demand")  # L1 score.py l. 14
OUT = "docs/evidence/mae_par_semaine.csv"


def weekly_mae(model, df: pd.DataFrame) -> pd.DataFrame:
    """One row per week of the valid and replay rows: model MAE against the lag_168h baseline."""
    valid_replay = df[df["split"].isin(("valid", "replay"))]
    monday = valid_replay["ts"].dt.to_period("W-SUN").dt.start_time  # a week runs from Monday to Sunday
    weeks = []
    for week, g in valid_replay.groupby(monday):  # groupby sorts the weeks
        mae_model = mae(model, g)
        mean_y = g["y"].mean()
        weeks.append(
            {
                "week": week.strftime("%Y-%m-%d"),
                "rows": len(g),
                "mean_y": mean_y,
                "mae_model": mae_model,
                "mae_baseline": baseline_mae(g),
                "mae_relative": mae_model / mean_y,
            }
        )
    return pd.DataFrame(weeks).round(3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MAE per week of the model behind an alias.")
    parser.add_argument("alias", nargs="?", default="production", help="registry alias (default: production)")
    parser.add_argument("--data", default=load_params()["data"]["features"], help="features Parquet file")
    args = parser.parse_args()

    # L1 score.py l. 12 and l. 18: the model is loaded by name and alias, never by path
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001"))
    model = mlflow.pyfunc.load_model(f"models:/{NAME}@{args.alias}")
    version = MlflowClient().get_model_version_by_alias(NAME, args.alias).version

    table = weekly_mae(model, pd.read_parquet(args.data))
    print(f"{NAME}@{args.alias} (v{version}) on {args.data}")
    print(table.to_string(index=False))
    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT, index=False)
    print(f"wrote {OUT}")
