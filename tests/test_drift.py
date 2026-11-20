import json

import numpy as np
import pandas as pd

from drift import make_reference, psi, reference_bins


def _data():
    rng = np.random.default_rng(0)
    ref_values = rng.poisson(20, 5000)
    sample = rng.choice(ref_values, 480)
    return ref_values, sample


def test_same_distribution_has_low_psi():
    ref_values, sample = _data()
    assert psi(reference_bins(ref_values), sample) < 0.1


def test_scaled_sample_has_high_psi():
    ref_values, sample = _data()
    assert psi(reference_bins(ref_values), sample * 0.2) > 0.25


def test_shares_sum_to_one():
    ref_values, _ = _data()
    assert np.isclose(sum(reference_bins(ref_values)["shares"]), 1.0)
    df = pd.DataFrame({"a": ref_values, "b": ref_values[::-1] * 2})
    ref = make_reference(df, ["a", "b"])
    json.dumps(ref)
    for f in ("a", "b"):
        assert np.isclose(sum(ref[f]["shares"]), 1.0)


def test_many_zeros_give_strictly_increasing_edges():
    rng = np.random.default_rng(1)
    values = np.where(rng.random(3000) < 0.6, 0, rng.poisson(5, 3000))
    edges = reference_bins(values)["edges"]
    assert np.all(np.diff(edges) > 0)
