"""Promotion by a human: @production takes the @staging version, and the move is logged.
Usage: uv run python promote.py   (then restart the API)
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")  # keep the terminal clean (L1 train.py l. 8)

import mlflow
from mlflow import MlflowClient

NAME = os.getenv("MODEL_NAME", "taxi-demand")  # L1 register.py l. 9
PROMOTIONS = "data/promotions.jsonl"  # one line per promotion (spec section 9), read by rollback.py


def promote() -> tuple[str, str]:
    """Point @production at the @staging version, log {"ts", "from", "to"}, return (from, to)."""
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001"))  # L1 register.py l. 8
    client = MlflowClient()
    # versions as text: a str via the server, an int with a local sqlite store, "1" in /health
    new = str(client.get_model_version_by_alias(NAME, "staging").version)  # the candidate (S5 p. 24)
    old = str(client.get_model_version_by_alias(NAME, "production").version)  # the version served now
    # a human moves @production (S5 p. 25); the old version stays in the Registry (WRAP p. 7)
    client.set_registered_model_alias(NAME, "production", new)  # L1 register.py l. 13
    # UTC time as in the JSON logs of S4 p. 34; the file is opened in append mode as in L4 app.py l. 49
    line = {"ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "from": old, "to": new}
    Path(PROMOTIONS).parent.mkdir(parents=True, exist_ok=True)  # data/ is ignored by Git, it may be missing
    with open(PROMOTIONS, "a") as f:
        f.write(json.dumps(line) + "\n")
    return old, new


if __name__ == "__main__":
    old, new = promote()
    print(f"{NAME} v{new} is now @production (was v{old})")  # L1 register.py l. 14
    print("Relancer l'API")  # the API loads the model once, at startup (S3 p. 26, spec section 7)
