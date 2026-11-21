"""Serve the taxi demand model @production as a REST API, with Prometheus metrics and a rolling input PSI.
Run with ONE worker, as in lab 4 (the PSI windows live in this process):
    uv run uvicorn app.main:app --port 8000
"""
import asyncio
import json
import logging
import os
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime

# L1 score.py l. 5-6: keep the terminal clean
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
os.environ.setdefault("MLFLOW_ENABLE_ARTIFACTS_PROGRESS_BAR", "false")

import mlflow
import numpy as np
import pandas as pd
import yaml
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from mlflow import MlflowClient
from prometheus_client import Counter, Gauge, Histogram, make_asgi_app
from pydantic import BaseModel, ConfigDict, Field

from drift import psi

MODEL_NAME = os.getenv("MODEL_NAME", "taxi-demand")  # spec section 1: os.getenv(NAME, contract value)
MODEL_ALIAS = os.getenv("MODEL_ALIAS", "production")
BUDGET_MS = 200  # L3 app.py l. 21
log = logging.getLogger("uvicorn.error")
state: dict = {}  # model, version, reference, PSI windows and prediction count: refilled by every lifespan

# L4 app.py l. 31-39: the three metrics of spec section 7
LATENCY = Histogram("taxi_request_seconds", "Request latency", ["endpoint"],
                    buckets=[0.01, 0.025, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6])
PREDICTIONS = Counter("taxi_predictions_total", "Predictions served", ["model_version"])
INPUT_PSI = Gauge("taxi_input_psi", "PSI of the last window against reference.json", ["feature"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once at startup (L3 app.py l. 26-37): load the model @production and its reference.json.
    If that fails the service still starts: /health says so and /v1/predict answers 503."""
    # Read here, not at import: the task 3.2 fixture points MLflow at a temporary store after importing the app
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001"))
    features = yaml.safe_load(open("params.yaml"))["features"]
    drift = yaml.safe_load(open("policy.yaml"))["drift"]
    # L4 app.py l. 28-29 and l. 42-43, sizes read from policy.yaml: one window per drift feature
    state.update(features=features, every=drift["every"], seen=0,
                 windows={f: deque(maxlen=drift["window"]) for f in drift["features"]})
    for f in drift["features"]:
        INPUT_PSI.labels(f).set(0)  # L4 app.py l. 73, even when no model loads
    try:
        mv = MlflowClient().get_model_version_by_alias(MODEL_NAME, MODEL_ALIAS)
        model = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}@{MODEL_ALIAS}")  # L1 score.py l. 18
        # L2 export_model.py l. 16, here for the drift reference logged in the model's run
        path = mlflow.artifacts.download_artifacts(run_id=mv.run_id, artifact_path="reference.json")
        reference = json.load(open(path))
        # str(): an int with a local sqlite:/// store (task 3.2 fixture), a str via the server
        state.update(model=model, version=str(mv.version), reference=reference)
        log.info("loaded models:/%s@%s (version %s)", MODEL_NAME, MODEL_ALIAS, state["version"])
    except Exception:  # L3 app.py l. 34 expects a missing file; here the alias, an artifact or the server can fail
        log.exception("no model at models:/%s@%s: running without a model", MODEL_NAME, MODEL_ALIAS)
    yield
    state.clear()


app = FastAPI(
    title="Taxi demand API",
    description="Predicts the yellow taxi pickups of one New York zone for the next hour.",
    version="1.0",
    lifespan=lifespan,
)
app.mount("/metrics", make_asgi_app())  # L4 app.py l. 80: Prometheus scrapes /metrics/


class PredictRequest(BaseModel):
    """The contract (spec section 7): what a caller must send. hour and dow are computed from ts."""

    model_config = ConfigDict(extra="forbid")  # L3 app.py l. 53: a misspelled field is an error, not silently ignored

    zone: int = Field(ge=1, le=265, description="TLC pickup zone (PULocationID)", examples=[237])
    ts: datetime = Field(description="Start of the hour to predict, New York local time without timezone",
                         examples=["2020-03-02T08:00:00"])
    # float, not int: JSON 112 becomes 112.0, the float64 that the model signature requires
    lag_1h: float = Field(ge=0, description="Pickups in the zone between ts - 1 h and ts", examples=[112.0])
    lag_24h: float = Field(ge=0, description="Pickups at the same hour, the day before", examples=[98.0])
    lag_168h: float = Field(ge=0, description="Pickups at the same hour, one week before", examples=[120.0])


class PredictResponse(BaseModel):
    zone: int
    ts: datetime
    prediction: float = Field(description="Predicted pickups in the zone between ts and ts + 1 h")
    model_version: str = Field(description="Registry version that answered, kept with the truth to compare later")


def score(row: dict) -> float:
    """One prediction. The DataFrame follows the model signature: zone, hour, dow int64; lags float64."""
    X = pd.DataFrame([row], columns=state["features"])
    return float(state["model"].predict(X)[0])


def observe(row: dict) -> None:
    """Count the prediction and feed the rolling PSI (L4 app.py l. 119-131)."""
    PREDICTIONS.labels(state["version"]).inc()
    for f, window in state["windows"].items():
        window.append(row[f])
    state["seen"] += 1
    if state["seen"] % state["every"] == 0:  # L4 app.py l. 130: every N predictions, once the window is full
        for f, window in state["windows"].items():
            if len(window) == window.maxlen:
                INPUT_PSI.labels(f).set(psi(state["reference"][f], np.array(window)))


@app.middleware("http")
async def tracing(request: Request, call_next):
    """Give every request an id and a timing header: what you grep for at 3 am (L3 app.py l. 96-107)."""
    request.state.request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:8])
    t0 = time.perf_counter()
    response = await call_next(request)
    seconds = time.perf_counter() - t0
    if request.url.path == "/v1/predict":
        LATENCY.labels(request.url.path).observe(seconds)  # L4 app.py l. 139-140
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Process-Time-Ms"] = f"{seconds * 1000:.1f}"
    if seconds * 1000 > BUDGET_MS:
        log.warning("SLOW %s %s %d %.0f ms", request.method, request.url.path, response.status_code, seconds * 1000)
    return response


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    """Never leak a stack trace to the caller; log it and return a small, stable error body (L3 app.py l. 110-115)."""
    rid = getattr(request.state, "request_id", "-")
    log.exception("unhandled error, request %s", rid)
    return JSONResponse(status_code=500, content={"detail": "internal error", "request_id": rid})


@app.get("/health", tags=["ops"])
async def health():
    """Is the service ready to predict? rollback.py and a load balancer read this (L3 app.py l. 118-123)."""
    if "model" not in state:
        return JSONResponse(status_code=503, content={"status": "degraded", "detail": "model not loaded"})
    return {"status": "ok", "model_version": state["version"]}


v1 = APIRouter(prefix="/v1", tags=["prediction"])  # L3 app.py l. 126: v2 can change the contract


@v1.post("/predict", responses={503: {"description": "No model loaded"}})
async def predict(req: PredictRequest) -> PredictResponse:
    """Predict the pickups of one zone for the hour that starts at ts."""
    if "model" not in state:
        raise HTTPException(status_code=503, detail="model not loaded")  # L3 app.py l. 141-142
    # Spec section 7: the API computes hour and dow from ts (Monday = 0, as in features.parquet)
    row = req.model_dump(exclude={"ts"}) | {"hour": req.ts.hour, "dow": req.ts.weekday()}
    prediction = await asyncio.to_thread(score, row)  # L3 app.py l. 92: keep the event loop free
    observe(row)
    return PredictResponse(zone=req.zone, ts=req.ts, prediction=prediction, model_version=state["version"])


app.include_router(v1)
