"""Integration tests of the API with a real registered model (task 3.2, L3 test_app.py)."""

VALID = {"zone": 237, "ts": "2020-03-02T08:00:00", "lag_1h": 112, "lag_24h": 98, "lag_168h": 120}


def test_health_shows_the_model_version(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["model_version"] == "1"


def test_valid_request_returns_a_number(client):
    r = client.post("/v1/predict", json=VALID)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["prediction"], float)
    assert body["zone"] == 237
    assert body["model_version"] == "1"
    assert r.headers["X-Request-ID"]


def test_same_request_gives_the_same_prediction(client):
    first = client.post("/v1/predict", json=VALID).json()["prediction"]
    second = client.post("/v1/predict", json=VALID).json()["prediction"]
    assert first == second


def test_extra_field_is_refused(client):
    r = client.post("/v1/predict", json=VALID | {"surge": 2})
    assert r.status_code == 422


def test_negative_lag_is_refused(client):
    r = client.post("/v1/predict", json=VALID | {"lag_1h": -1})
    assert r.status_code == 422


def test_zone_out_of_range_is_refused(client):
    r = client.post("/v1/predict", json=VALID | {"zone": 0})
    assert r.status_code == 422


def test_metrics_expose_predictions_and_psi(client):
    client.post("/v1/predict", json=VALID)
    text = client.get("/metrics/").text
    assert "taxi_predictions_total" in text
    assert "taxi_input_psi" in text
