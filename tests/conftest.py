"""Shared fixture for the API tests (task 3.2): a real model, registered in a throwaway MLflow store.

No MLflow server and no network: the store is a SQLite file in a temporary folder, so the same
tests run on a laptop and in GitHub Actions (S3 p. 29: "register a test model").
"""
import os

import mlflow
import pytest
import yaml
from fastapi.testclient import TestClient

from drift import make_reference
from make_synthetic import make_synthetic
from register import register
from train import fit, load_params, log_model_run


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    """Train on the synthetic data, register the model @production, then start the API on it."""
    tmp = tmp_path_factory.mktemp("mlflow")
    uri = f"sqlite:///{tmp / 'mlflow.db'}"
    old_uri = os.environ.get("MLFLOW_TRACKING_URI")
    # train.py, register.py and the API lifespan all read this variable
    os.environ["MLFLOW_TRACKING_URI"] = uri
    mlflow.set_tracking_uri(uri)

    params = load_params()
    policy = yaml.safe_load(open("policy.yaml"))
    # artifacts in the temporary folder too, not in ./mlruns of the repo
    mlflow.create_experiment(params["mlflow"]["experiment"], artifact_location=(tmp / "artifacts").as_uri())

    df = make_synthetic()
    data_path = tmp / "synthetic.parquet"
    df.to_parquet(data_path, index=False)  # log_model_run reads it for the signature and data_md5
    model = fit(params, df)
    reference = make_reference(df[df["split"] == "train"], policy["drift"]["features"], policy["drift"]["bins"])
    run_id = log_model_run(model, params, {"mae_valid": 0.0}, reference, str(data_path))
    register(run_id, "production")

    from app.main import app  # imported here: the lifespan reads MLFLOW_TRACKING_URI at startup

    with TestClient(app) as c:  # "with" runs the lifespan, as in L3 test_app.py l. 9-12
        yield c

    if old_uri is None:
        os.environ.pop("MLFLOW_TRACKING_URI", None)
    else:
        os.environ["MLFLOW_TRACKING_URI"] = old_uri
