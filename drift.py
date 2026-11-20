"""Drift helpers: quantile reference bins and PSI (course lab 4 formula)."""
import numpy as np


def reference_bins(values, bins=10) -> dict:
    """Quantile edges and measured share of values per bin, as JSON-ready lists."""
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
    reference_edges, reference_share = ref["edges"], ref["shares"]
    counts = np.histogram(np.clip(sample, reference_edges[0], reference_edges[-1]), reference_edges)[0]
    live = np.clip(counts / counts.sum(), 1e-4, None)
    ref = np.clip(reference_share, 1e-4, None)
    return float(np.sum((live - ref) * np.log(live / ref)))
