"""Retraining trigger (task 5.2): look at the replayed traffic, decide, retrain and pass the gate.

Usage: uv run python check_and_retrain.py

Chain from the course (S5 p. 22-27): PSI above the threshold and no cooldown -> train a candidate
on recent data -> gate against @production on the last days -> @staging if it is better.
A human then runs promote.py: this script never touches @production.
"""
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")  # keep the terminal clean (L1 train.py l. 8)
os.environ.setdefault("MLFLOW_ENABLE_ARTIFACTS_PROGRESS_BAR", "false")

import mlflow
import pandas as pd
import yaml
from mlflow import MlflowClient

from drift import make_reference, psi
from register import register
from train import fit, load_params, log_model_run, mae

NAME = os.getenv("MODEL_NAME", "taxi-demand")
TRUTH = "data/truth.csv"  # written by replay.py (spec section 9)
DECISIONS = "data/decisions.jsonl"  # one line per run of this script (spec section 9)
LOCK = "data/check_and_retrain.lock"  # one run at a time (S5 p. 32)


def decide(psi_max: float, days: int, days_since_retrain, policy: dict) -> str:
    """The course decision tree (S5 p. 22), in this order:
    wait     : not enough new days to judge
    watch    : the inputs have not moved enough
    cooldown : a retrain happened too recently
    retrain  : otherwise
    days_since_retrain is None when the model was never retrained by this script.
    """
    retrain = policy["retrain"]
    if days < retrain["min_new_days"]:
        return "wait"
    if psi_max < policy["drift"]["psi_act"]:
        return "watch"
    if days_since_retrain is not None and days_since_retrain < retrain["cooldown_days"]:
        return "cooldown"
    return "retrain"


def last_window(truth: pd.DataFrame, n_days: int) -> pd.DataFrame:
    """Rows of the last n_days calendar days, counted back from the last replayed hour."""
    last_day = truth["ts"].max().normalize()
    return truth[truth["ts"] >= last_day - pd.Timedelta(days=n_days - 1)]


def days_since_last_retrain(now: pd.Timestamp):
    """Simulated days between now and the last "retrain" in decisions.jsonl, or None if there is none."""
    if not Path(DECISIONS).exists():
        return None
    retrains = [json.loads(line) for line in open(DECISIONS) if line.strip()]
    retrains = [d for d in retrains if d["action"] == "retrain"]
    if not retrains:
        return None
    return (now - pd.Timestamp(retrains[-1]["now"])).total_seconds() / 86400


def load_truth() -> pd.DataFrame:
    truth = pd.read_csv(TRUTH, parse_dates=["ts"])
    # a period replayed twice appends the same hours again: keep the last answer per zone and hour
    return truth.drop_duplicates(["ts", "zone"], keep="last").sort_values(["ts", "zone"]).reset_index(drop=True)


def check() -> dict:
    params = load_params()
    policy = yaml.safe_load(open("policy.yaml"))
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001"))

    truth = load_truth()
    now = truth["ts"].max()
    window = last_window(truth, policy["retrain"]["window_days"])
    days = int(window["ts"].dt.normalize().nunique())

    # the reference of the version served now, as in the API (task 3.1)
    production = MlflowClient().get_model_version_by_alias(NAME, "production")
    path = mlflow.artifacts.download_artifacts(run_id=production.run_id, artifact_path="reference.json")
    reference = json.load(open(path))
    psis = {f: round(psi(reference[f], window[f].to_numpy()), 4) for f in policy["drift"]["features"]}
    since = days_since_last_retrain(now)

    action = decide(max(psis.values()), days, since, policy)
    line = {"now": now.isoformat(), "psi": psis, "days": days, "action": action,
            "mae_production": None, "mae_candidate": None, "run_id": None, "version": None}

    if action == "retrain":
        holdout = last_window(window, policy["retrain"]["holdout_days"])
        recent = window[window["ts"] < holdout["ts"].min()].assign(split="train")
        candidate = fit(params, recent)
        prod_model = mlflow.pyfunc.load_model(f"models:/{NAME}@production")
        mae_candidate, mae_production = mae(candidate, holdout), mae(prod_model, holdout)
        # the candidate's own drift reference, measured on the rows it was trained on
        cand_reference = make_reference(recent, policy["drift"]["features"], policy["drift"]["bins"])
        run_id = log_model_run(candidate, params,
                               {"mae_holdout": mae_candidate, "mae_holdout_production": mae_production},
                               cand_reference, TRUTH)
        line |= {"mae_production": round(mae_production, 4), "mae_candidate": round(mae_candidate, 4),
                 "run_id": run_id}
        # the gate (S5 p. 31): at least min_gain better than production on the same recent hours
        if mae_candidate <= (1 - policy["retrain"]["min_gain"]) * mae_production:
            line["version"] = register(run_id, "staging")
        else:
            line["action"] = "refused"  # "Fail at the gate: the old model stays in production" (S5 p. 24)

    Path(DECISIONS).parent.mkdir(parents=True, exist_ok=True)
    with open(DECISIONS, "a") as f:
        f.write(json.dumps(line) + "\n")
    return line


def main() -> None:
    if not Path(TRUTH).exists():
        sys.exit(f"{TRUTH} is missing: run replay.py first")
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)  # fails if another run holds the lock
    except FileExistsError:
        sys.exit(f"another check is running (delete {LOCK} if it crashed)")
    try:
        line = check()
    finally:
        os.close(fd)
        os.remove(LOCK)

    print(json.dumps(line))
    action = line["action"]
    if action == "retrain":
        print(f"{NAME} v{line['version']} is now @staging "
              f"(MAE {line['mae_candidate']} vs {line['mae_production']} in production)")
        print("Next: uv run python promote.py, then restart the API")
    elif action == "refused":
        print(f"candidate refused at the gate (MAE {line['mae_candidate']} vs {line['mae_production']}): "
              "production stays as it is")
    else:
        print(f"decision: {action}")


if __name__ == "__main__":
    main()
