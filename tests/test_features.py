"""Tests of build_features on trips made by hand: 9 days, 2 zones, split dates passed as parameters.
No file of data/ and no network, so the CI can run them.
"""
import numpy as np
import pandas as pd
import pytest

from build_dataset import build_features

PARAMS = {  # not params.yaml: one train day, then valid and replay on the next day
    "data": {"months": ["2020-01"], "n_zones": 2},
    "split": {
        "train": ["2020-01-08 00:00", "2020-01-08 23:00"],
        "valid": ["2020-01-09 00:00", "2020-01-09 11:00"],
        "replay": ["2020-01-09 12:00", "2020-01-09 23:00"],
    },
}
COLUMNS = ["ts", "zone", "hour", "dow", "lag_1h", "lag_24h", "lag_168h", "y", "split"]  # spec section 4
ZONES = (132, 237)
HOURS = pd.date_range("2020-01-01 00:00", "2020-01-09 23:00", freq="h")  # the 9 days of trips
KEPT = pd.date_range("2020-01-08 00:00", "2020-01-09 23:00", freq="h")  # the 48 hours of the 3 ranges
EMPTY_HOUR = pd.Timestamp("2020-01-08 03:00")  # zone 237 has no trip in this train hour
OUTSIDE = [("2019-12-31 23:30", 132), ("2020-02-01 00:10", 237)]  # out of the period: counted nowhere
H = pd.Timedelta(hours=1)


def make_trips() -> pd.DataFrame:
    """0 to 5 trips per zone and hour (fixed seed), at different minutes of the hour, plus OUTSIDE."""
    rng = np.random.default_rng(0)
    rows = []
    for zone in ZONES:
        for hour in HOURS:
            # no trip in any zone in HOURS[0]: the grid must start with the period, not the first trip
            empty = hour == HOURS[0] or (zone, hour) == (237, EMPTY_HOUR)
            n = 0 if empty else int(rng.integers(0, 6))
            # first trip at hh:00:00, last one at hh:59:59: floor("h") must keep both in hour hh
            rows += [(hour + pd.Timedelta(seconds=int(s)), zone) for s in np.linspace(0, 3599, n)]
    rows += [(pd.Timestamp(t), zone) for t, zone in OUTSIDE]
    trips = pd.DataFrame(rows, columns=["tpep_pickup_datetime", "PULocationID"])
    # same types as the TLC files (docs/data.md), shuffled: the result must not depend on the order
    trips = trips.astype({"tpep_pickup_datetime": "datetime64[us]", "PULocationID": "int64"})
    return trips.sample(frac=1, random_state=0).reset_index(drop=True)


TRIPS = make_trips()


def count(zone, start, end) -> int:
    """Trips of the zone with start <= pickup time < end, counted directly on TRIPS."""
    t = TRIPS["tpep_pickup_datetime"]
    return int(((TRIPS["PULocationID"] == zone) & (t >= start) & (t < end)).sum())


@pytest.fixture(scope="module")
def built():
    # module scope as in L3 test_app.py: one call for the four tests of step 6, on a copy so TRIPS stays as made
    return build_features(TRIPS.copy(), PARAMS)


def test_one_row_per_zone_and_hour(built):
    """96 rows: the 2 zones x the 48 hours of the three ranges, once each, with the columns of section 4."""
    features, zones = built
    assert isinstance(zones, list) and zones == [132, 237]
    assert [type(z) for z in zones] == [int, int]  # plain ints, so json.dump can write data/zones.json
    assert list(features.columns) == COLUMNS
    assert len(features) == 2 * 48
    assert not features.duplicated(["zone", "ts"]).any()
    for zone in zones:
        assert features.loc[features["zone"] == zone, "ts"].sort_values().tolist() == KEPT.tolist()
    # types and calendar columns of section 4 (ts: any datetime64 unit, the TLC files give us)
    assert pd.api.types.is_datetime64_dtype(features["ts"])
    assert features[["zone", "hour", "dow"]].dtypes.astype(str).tolist() == ["int64"] * 3
    assert features[["lag_1h", "lag_24h", "lag_168h", "y"]].dtypes.astype(str).tolist() == ["float64"] * 4
    assert pd.api.types.is_string_dtype(features["split"])
    assert features["hour"].tolist() == features["ts"].dt.hour.tolist()
    assert features["dow"].tolist() == features["ts"].dt.day_of_week.tolist()  # Monday = 0
    assert features.loc[features["ts"] == KEPT[0], "dow"].tolist() == [2, 2]  # 2020-01-08 was a Wednesday


def test_lag_1h_is_the_trip_count_of_the_previous_hour(built):
    """lag_1h = trips of the zone in [ts - 1 h, ts); y, lag_24h and lag_168h are checked the same way."""
    features, _ = built
    rows = list(zip(features["zone"], features["ts"]))  # expected values come from TRIPS, not from features
    assert features["lag_1h"].tolist() == [count(z, ts - H, ts) for z, ts in rows]
    assert features["y"].tolist() == [count(z, ts, ts + H) for z, ts in rows]
    assert features["lag_24h"].tolist() == [count(z, ts - 24 * H, ts - 23 * H) for z, ts in rows]
    assert features["lag_168h"].tolist() == [count(z, ts - 168 * H, ts - 167 * H) for z, ts in rows]


def test_hour_without_trips_is_zero(built):
    """An hour without trips counts 0: as y, then as lag_1h, lag_24h and lag_168h of the later hours."""
    features, _ = built
    assert count(237, EMPTY_HOUR, EMPTY_HOUR + H) == 0  # the made-up data really has no trip there
    zone_237 = features[features["zone"] == 237].set_index("ts")
    assert zone_237.loc[EMPTY_HOUR, "y"] == 0
    assert zone_237.loc[EMPTY_HOUR + H, "lag_1h"] == 0
    assert zone_237.loc[EMPTY_HOUR + 24 * H, "lag_24h"] == 0
    # the grid starts with the period, 7 days before the train range, although HOURS[0] has no trip
    assert features.loc[features["ts"] == KEPT[0], "lag_168h"].tolist() == [0, 0]
    assert features[["lag_1h", "lag_24h", "lag_168h"]].isna().sum().tolist() == [0, 0, 0]


def test_no_train_row_after_the_train_range(built):
    """No "train" row after the end of the train range; each split value stays inside its own range."""
    features, _ = built
    train_end = pd.Timestamp(PARAMS["split"]["train"][1])
    assert features.loc[features["split"] == "train", "ts"].max() <= train_end
    assert features["split"].value_counts().to_dict() == {"train": 48, "valid": 24, "replay": 24}
    for name, (start, end) in PARAMS["split"].items():
        ts = features.loc[features["split"] == name, "ts"]
        assert pd.Timestamp(start) <= ts.min() and ts.max() <= pd.Timestamp(end), name


def test_lags_never_come_from_another_zone():
    """With a train range that starts with the period, the first hour of each zone has no past: its lags
    are missing, never taken from the zone sorted before it (EC-1, groupby("zone") before shift)."""
    params = {**PARAMS, "split": {**PARAMS["split"], "train": ["2020-01-01 00:00", "2020-01-08 23:00"]}}
    features, _ = build_features(TRIPS.copy(), params)
    first_hour = features[features["ts"] == HOURS[0]]
    assert first_hour["zone"].tolist() == [132, 237]
    assert first_hour[["lag_1h", "lag_24h", "lag_168h"]].isna().all().all()
