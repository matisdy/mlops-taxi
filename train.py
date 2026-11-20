"""Train the taxi demand model and log everything that matters to MLflow.
Usage: uv run python train.py [--data data/synthetic.parquet]
"""
import argparse
import hashlib
import os
import subprocess
from pathlib import Path

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")  # keep the terminal clean (L1 train.py l. 8)

import mlflow
import pandas as pd
import yaml
from mlflow.models import infer_signature
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from drift import make_reference


def load_params(path="params.yaml") -> dict:
    # L1 train.py l. 25-30, without the key=value overrides
    return yaml.safe_load(open(path))


def fit(params: dict, df: pd.DataFrame) -> Pipeline:
    """Pure function: same params + same data => same model. No MLflow in here."""
    # L1 train.py l. 33-53, as a regressor trained on the "train" rows (spec section 5)
    train = df[df["split"] == "train"]
    X, y = train[params["features"]], train[params["target"]]
    pre = ColumnTransformer(
        [("zone", OneHotEncoder(handle_unknown="ignore"), ["zone"])],
        remainder="passthrough",
    )
    reg = HistGradientBoostingRegressor(
        max_iter=params["model"]["max_iter"],
        learning_rate=params["model"]["learning_rate"],
        random_state=params["model"]["random_state"],
    )
    return Pipeline([("pre", pre), ("reg", reg)]).fit(X, y)


def mae(model, df: pd.DataFrame) -> float:
    """MAE on the rows of df, for the Pipeline of fit() or a pyfunc model loaded from MLflow."""
    params = load_params()
    return float(mean_absolute_error(df[params["target"]], model.predict(df[params["features"]])))


def baseline_mae(df: pd.DataFrame) -> float:
    """MAE of the baseline that predicts the same hour one week before, lag_168h (S1-INTRO p. 28)."""
    return float(mean_absolute_error(df[load_params()["target"]], df["lag_168h"]))


def git(*args: str) -> str:
    # L1 train.py l. 56-57
    return subprocess.check_output(["git", *args], text=True).strip()


def data_md5(path: str) -> str:
    """The data's fingerprint, read from the small .dvc file that Git tracks."""
    if Path(f"{path}.dvc").exists():
        return yaml.safe_load(open(f"{path}.dvc"))["outs"][0]["md5"]  # L1 train.py l. 60-62
    return hashlib.md5(Path(path).read_bytes()).hexdigest()  # no .dvc pointer: same md5 as DVC 3


def log_model_run(model, params: dict, metrics: dict, reference: dict, data_path: str) -> str:
    """Log one run (params, metrics, tags, model, reference.json) and return its run_id."""
    # L1 train.py l. 67-68: URI from the environment, experiment name from params.yaml
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001"))
    mlflow.set_experiment(params["mlflow"]["experiment"])
    with mlflow.start_run() as run:
        # L1 l. 73-82: params (model.* and the split dates), metrics, then the three tags
        run_params = {f"model.{key}": value for key, value in params["model"].items()}
        for name, (start, end) in params["split"].items():
            run_params |= {f"split.{name}_start": start, f"split.{name}_end": end}
        mlflow.log_params(run_params)
        mlflow.log_metrics(metrics)
        mlflow.set_tags(
            {
                "git_commit": git("rev-parse", "HEAD"),
                "git_dirty": str(bool(git("status", "--porcelain"))),
                "data_md5": data_md5(data_path),
            }
        )
        # L1 l. 83-90; regression: no pyfunc_predict_fn, the model serves the predicted value
        df = pd.read_parquet(data_path)
        X_valid = df.loc[df["split"] == "valid", params["features"]]  # the lab's X_te
        mlflow.sklearn.log_model(
            model,
            name="model",
            skops_trusted_types=["sklearn.ensemble._hist_gradient_boosting.predictor.TreePredictor"],  # we trust our own model
            signature=infer_signature(X_valid, model.predict(X_valid)),
            input_example=X_valid.head(3),
        )
        mlflow.log_dict(reference, "reference.json")  # drift reference, a run artifact (S1-MLF p. 20)
    return run.info.run_id


if __name__ == "__main__":
    params = load_params()
    parser = argparse.ArgumentParser(description="Train the model and log the run to MLflow.")
    parser.add_argument("--data", default=params["data"]["features"], help="features Parquet file")
    path = parser.parse_args().data
    policy = yaml.safe_load(open("policy.yaml"))

    df = pd.read_parquet(path)
    model = fit(params, df)
    valid = df[df["split"] == "valid"]
    metrics = {"mae_valid": mae(model, valid), "mae_baseline_valid": baseline_mae(valid)}
    # reference.json: drift bins measured on the training rows (spec section 5)
    reference = make_reference(df[df["split"] == "train"], policy["drift"]["features"], policy["drift"]["bins"])
    run_id = log_model_run(model, params, metrics, reference, path)
    print(f"mae_valid {metrics['mae_valid']:.4f} | mae_baseline_valid {metrics['mae_baseline_valid']:.4f}")
    print(f"run_id = {run_id}")  # L1 train.py l. 91-92
