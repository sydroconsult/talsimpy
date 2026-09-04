import datetime
import math

import numpy as np
import pandas as pd
import pytest

from talsimpy import Timeseries


def make_ts(title="test"):
    ts = Timeseries(title)
    ts.add_node(datetime.datetime(2020, 1, 1), 1.0)
    ts.add_node(datetime.datetime(2020, 1, 2), 2.0)
    ts.add_node(datetime.datetime(2020, 1, 3), 3.0)
    return ts


def test_add_node_and_getitem():
    ts = Timeseries()
    ts.add_node(datetime.datetime(2020, 1, 1), 5.0)
    assert ts[datetime.datetime(2020, 1, 1)] == 5.0


def test_add_node_accepts_date_and_converts_to_datetime():
    ts = Timeseries()
    ts.add_node(datetime.date(2020, 1, 1), 5.0)
    assert ts[datetime.datetime(2020, 1, 1)] == 5.0


def test_add_node_rejects_invalid_timestamp():
    ts = Timeseries()
    with pytest.raises(ValueError):
        ts.add_node("2020-01-01", 5.0)


def test_setitem_is_equivalent_to_add_node():
    ts = Timeseries()
    ts[datetime.datetime(2020, 1, 1)] = 5.0
    assert ts.nodes[datetime.datetime(2020, 1, 1)] == 5.0


def test_len_and_iter():
    ts = make_ts()
    assert len(ts) == 3
    assert [v for _, v in ts] == [1.0, 2.0, 3.0]


def test_dates_and_values_are_sorted():
    ts = Timeseries()
    ts.add_node(datetime.datetime(2020, 1, 3), 3.0)
    ts.add_node(datetime.datetime(2020, 1, 1), 1.0)
    ts.add_node(datetime.datetime(2020, 1, 2), 2.0)
    assert ts.dates == [
        datetime.datetime(2020, 1, 1),
        datetime.datetime(2020, 1, 2),
        datetime.datetime(2020, 1, 3),
    ]
    assert ts.values == [1.0, 2.0, 3.0]


def test_start_and_end():
    ts = make_ts()
    assert ts.start == datetime.datetime(2020, 1, 1)
    assert ts.end == datetime.datetime(2020, 1, 3)


def test_start_and_end_of_empty_series_are_none():
    ts = Timeseries()
    assert ts.start is None
    assert ts.end is None


def test_cut_keeps_only_nodes_within_range_inclusive():
    ts = make_ts()
    ts.cut(datetime.datetime(2020, 1, 2), datetime.datetime(2020, 1, 3))
    assert ts.dates == [datetime.datetime(2020, 1, 2), datetime.datetime(2020, 1, 3)]


def test_copy_is_independent_from_original():
    ts = make_ts()
    ts_copy = ts.copy()
    ts_copy.add_node(datetime.datetime(2020, 1, 4), 4.0)
    assert len(ts) == 3
    assert len(ts_copy) == 4
    assert ts_copy.title == ts.title


def test_copy_metadata():
    ts1 = make_ts()
    ts1.unit = "m3/s"
    ts1.station_name = "Station A"
    ts2 = Timeseries()
    ts2.copy_metadata(ts1)
    assert ts2.unit == "m3/s"
    assert ts2.station_name == "Station A"
    # nodes are not copied by copy_metadata
    assert len(ts2) == 0


def test_count_value_nodes_ignores_nan():
    ts = make_ts()
    ts.add_node(datetime.datetime(2020, 1, 4), np.nan)
    assert ts.count_value_nodes() == 3


def test_delete_nan_nodes():
    ts = make_ts()
    ts.add_node(datetime.datetime(2020, 1, 4), np.nan)
    ts.delete_nan_nodes()
    assert len(ts) == 3
    assert all(not math.isnan(v) for v in ts.values)


def test_delete_negative_nodes():
    ts = make_ts()
    ts.add_node(datetime.datetime(2020, 1, 4), -1.0)
    ts.delete_negative_nodes()
    assert len(ts) == 3
    assert all(v >= 0 for v in ts.values)


def test_fill_gaps_daily_inserts_nan_for_missing_days():
    ts = Timeseries()
    ts.add_node(datetime.datetime(2020, 1, 1), 1.0)
    ts.add_node(datetime.datetime(2020, 1, 3), 3.0)
    ts.fill_gaps(dt="d")
    assert len(ts) == 3
    assert math.isnan(ts[datetime.datetime(2020, 1, 2)])


def test_add_months_handles_year_rollover_and_shorter_months():
    result = Timeseries._add_months(datetime.datetime(2020, 12, 31), 2)
    assert result == datetime.datetime(2021, 2, 28)


def test_synchronize_keeps_only_common_dates():
    ts1 = make_ts()
    ts2 = Timeseries()
    ts2.add_node(datetime.datetime(2020, 1, 2), 20.0)
    ts2.add_node(datetime.datetime(2020, 1, 4), 40.0)

    ts1_sync, ts2_sync = Timeseries.synchronize(ts1, ts2)

    assert ts1_sync.dates == [datetime.datetime(2020, 1, 2)]
    assert ts2_sync.dates == [datetime.datetime(2020, 1, 2)]
    # originals are untouched
    assert len(ts1) == 3
    assert len(ts2) == 2


def test_date_to_double_and_back_roundtrip():
    timestamp = datetime.datetime(2020, 1, 1, 12, 0, 0)
    rdate = Timeseries._date_to_double(timestamp)
    assert Timeseries._double_to_date(rdate) == timestamp


def test_to_dataframe_and_from_series_roundtrip():
    ts = make_ts()
    df = Timeseries.to_dataframe(ts)
    assert list(df.columns) == ["test"]
    assert df["test"].tolist() == [1.0, 2.0, 3.0]

    series = df["test"]
    ts_roundtrip = Timeseries.from_series(series)
    assert ts_roundtrip.dates == ts.dates
    assert ts_roundtrip.values == ts.values


@pytest.mark.parametrize("suffix", ["uvf", "zrx", "bin"])
def test_write_and_read_file_roundtrip(tmp_path, suffix):
    ts = make_ts("roundtrip")
    ts.unit = "m3/s"
    ts.location = "Teststation"

    filename = tmp_path / f"ts.{suffix}"
    ts.write_to_file(filename)

    ts_read = Timeseries.read_file(filename)

    assert ts_read.dates == ts.dates
    assert ts_read.values == pytest.approx(ts.values)
