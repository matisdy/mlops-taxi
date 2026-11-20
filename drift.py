"""Drift helpers: quantile reference bins and PSI (course lab 4 formula)."""
import numpy as np


def reference_bins(values, bins=10) -> dict:
    """Quantile edges and measured share of values per bin, as JSON-ready lists."""
    values = np.asarray(values)
    edges = np.unique(np.quantile(values, np.linspace(0, 1, bins + 1)))
    # Shares are measured on the data (not fixed at 10 % per bin as in lab 4):
    # on counts, several deciles can coincide (EC-8).
    shares = np.histogram(values, edges)[0] / len(values)
    return {"edges": edges.tolist(), "shares": shares.tolist()}


def make_reference(df, features, bins=10) -> dict:
    """Build the reference.json content: one reference_bins per feature."""
    return {f: reference_bins(df[f].to_numpy(), bins) for f in features}


def psi(ref, sample) -> float:
    """Population Stability Index of a sample against a reference_bins dict."""
    # Formula from Lab Session 4 (monitoring), app.py l. 59-63.
    edges = np.asarray(ref["edges"])
    ref_share = np.maximum(np.asarray(ref["shares"]), 1e-4)
    sample = np.clip(np.asarray(sample), edges[0], edges[-1])
    live = np.histogram(sample, edges)[0] / len(sample)
    live = np.maximum(live, 1e-4)
    return float(np.sum((live - ref_share) * np.log(live / ref_share)))
