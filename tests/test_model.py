"""Model tests on the synthetic data: no MLflow server and no network, so the CI can run them."""
import numpy as np

from make_synthetic import make_synthetic
from train import baseline_mae, fit, load_params, mae


def test_two_fits_give_the_same_predictions():
    # Same params + same data => same model (L1 train.py l. 34; L1 repro_check.py l. 24-27)
    params, df = load_params(), make_synthetic()
    first, second = fit(params, df), fit(params, df)
    X = df[params["features"]]
    assert np.array_equal(first.predict(X), second.predict(X))


def test_mae_and_baseline_are_positive():
    params, df = load_params(), make_synthetic()
    valid = df[df["split"] == "valid"]
    model = fit(params, df)
    assert mae(model, valid) > 0
    assert baseline_mae(valid) > 0


def test_fit_works_with_20_zones():
    # 20 zones make the one-hot output sparse, which the regressor refuses; 3 zones do not show it
    params, df = load_params(), make_synthetic(zones=tuple(range(1, 21)))
    model = fit(params, df)
    assert len(model.predict(df[params["features"]])) == len(df)
