"""Model tests on the synthetic data: no MLflow server and no network, so the CI can run them."""
import numpy as np

from make_synthetic import make_synthetic
from train import baseline_mae, fit, load_params, mae


def test_two_fits_give_the_same_predictions():
    # Same params + same data => same model (L1 train.py l. 34; L1 repro_check.py l. 24-27)
    first = fit(load_params(), make_synthetic())
    second = fit(load_params(), make_synthetic())
    X = make_synthetic()[load_params()["features"]]
    assert np.array_equal(first.predict(X), second.predict(X))


def test_mae_and_baseline_are_positive():
    df = make_synthetic()
    valid = df[df["split"] == "valid"]
    model = fit(load_params(), df)
    assert mae(model, valid) > 0
    assert baseline_mae(valid) > 0
