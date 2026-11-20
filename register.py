"""Put a run's model in the MLflow Registry and give it an alias.
Usage: uv run python register.py RUN_ID [alias]   (default alias: production)
"""
import os
import sys

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")  # keep the terminal clean (L1 train.py l. 8)

import mlflow
from mlflow import MlflowClient

NAME = os.getenv("MODEL_NAME", "taxi-demand")  # L1 register.py l. 9


def register(run_id: str, alias: str) -> str:
    """Register the run's model as a new version of NAME, point the alias at it, return the version."""
    # L1 register.py l. 8, inside the function so that scripts importing register() use it too
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001"))
    # L1 register.py l. 12-13: a new version of NAME, then the alias moves onto it
    version = mlflow.register_model(f"runs:/{run_id}/model", NAME)
    MlflowClient().set_registered_model_alias(NAME, alias, version.version)
    return version.version


if __name__ == "__main__":
    # L1 register.py l. 11, with production as the default alias (spec section 6)
    run_id, alias = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "production")
    version = register(run_id, alias)
    print(f"{NAME} v{version} is now @{alias}")  # L1 register.py l. 14
