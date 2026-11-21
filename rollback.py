"""Rollback: @production goes back to VERSION, or to the "from" of the last promotion, and it is timed.
Usage: uv run python rollback.py [VERSION]   (then restart the API: the script waits for /health)
"""
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")  # keep the terminal clean (L1 train.py l. 8)

import httpx
import mlflow
from mlflow import MlflowClient

NAME = os.getenv("MODEL_NAME", "taxi-demand")  # L1 register.py l. 9
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")  # .env.example (spec section 3)
PROMOTIONS = "data/promotions.jsonl"  # written by promote.py (spec section 9)
POLL_SECONDS = 2  # ask /health every 2 s, like "until nslookup redis; do sleep 2; done" (S6 p. 17)
TIMEOUT_SECONDS = 300  # a rollback takes under 5 minutes (S6 p. 36)


def rollback(target: str) -> float:
    """Point @production at version target, wait until /health serves it, return the seconds it took."""
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001"))  # L1 register.py l. 8
    # the clock starts just before the alias moves (time.time() as in L4 traffic.py l. 73), like timing
    # `rollout undo` then `rollout status` (S6-LAB TD_kubernetes.ipynb l. 809-819, Q12 l. 847)
    start = time.time()
    # rollback = move the alias back (S5 p. 25, WRAP p. 7)
    MlflowClient().set_registered_model_alias(NAME, "production", target)  # L1 register.py l. 13
    print(f"{NAME} v{target} is now @production")  # L1 register.py l. 14
    # the API loads the model once, at startup (S3 p. 26, spec section 7)
    print("Relancer l'API", flush=True)  # flush: shown at once, even when the output goes to a file or tee
    deadline = start + TIMEOUT_SECONDS  # L4 traffic.py l. 73
    while time.time() < deadline:  # L4 traffic.py l. 86
        try:  # the API is restarting: a refused connection or a 503 is not fatal (L4 traffic.py l. 46-50)
            r = httpx.get(f"{API_URL}/health", timeout=2)  # httpx: L4 traffic.py l. 18; timeout: S3 p. 8
            # 200 {"status": "ok", "model_version": "1"} (spec section 7): versions are compared as text
            if r.status_code == 200 and str(r.json()["model_version"]) == target:
                return time.time() - start
        except httpx.HTTPError:  # L4 traffic.py l. 49-50
            pass
        time.sleep(POLL_SECONDS)
    sys.exit(f"/health did not show v{target} within {TIMEOUT_SECONDS} s")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        lines = Path(PROMOTIONS).read_text().splitlines() if Path(PROMOTIONS).exists() else []
        if not lines:
            sys.exit(f"no promotion in {PROMOTIONS}: give the VERSION, e.g. uv run python rollback.py 1")
        target = json.loads(lines[-1])["from"]  # every promoted version keeps its predecessor (S5 p. 32)
    seconds = rollback(target)
    print(f"/health shows v{target} after {seconds:.1f} s")
