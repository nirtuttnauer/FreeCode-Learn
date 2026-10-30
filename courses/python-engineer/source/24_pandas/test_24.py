import time

import numpy as np
import pandas as pd
import pytest

from courselib import impl

m = impl("24")

RAW = pd.DataFrame(
    {
        "order_id": ["1", "2", "3", "4", "5", "6", "2", "7"],
        "customer_id": ["10", "10", "20", "20", "30", "oops", "10", "30"],
        "ts": [
            "2026-01-05 10:00:00",
            "2026-01-20 11:00:00",
            "2026-02-03 09:30:00",
            "2026-02-14 18:45:00",
            "2026-03-01 00:00:00",
            "2026-03-02 00:00:00",
            "2026-01-20 11:00:00",
            "not a date",
        ],
        "amount": ["100.0", "50.5", "200", "-5", "abc", "75", "50.5", "10"],
        "status": ["complete", "complete", "complete", "complete", "complete", "weird", "complete", "pending"],
        "region": [" North ", "north", "SOUTH", "south", "north", "south", "north", "south"],
    }
)


@pytest.fixture
def clean():
    return m.clean_orders(RAW)


class TestCleanOrders:
    def test_drops_unusable_rows(self, clean):
        # order 4 (negative), 5 (bad amount), 7 (bad date), duplicate 2 -> 4 rows left
        assert list(clean["order_id"]) == [1, 2, 3, 6]

    def test_dtypes(self, clean):
        assert clean["order_id"].dtype == "Int64"
        assert clean["customer_id"].dtype == "Int64"
        assert clean["amount"].dtype == "float64"
        assert isinstance(clean["ts"].dtype, pd.DatetimeTZDtype)
        assert str(clean["status"].dtype) == "category"

    def test_timestamps_are_utc(self, clean):
        assert str(clean["ts"].dt.tz) == "UTC"

    def test_region_normalised(self, clean):
        assert set(clean["region"]) <= {"north", "south"}
        assert clean.loc[0, "region"] == "north"

    def test_unknown_status_becomes_na(self, clean):
        assert list(clean["status"].cat.categories) == ["complete", "pending", "cancelled"]
        assert clean.loc[clean["order_id"] == 6, "status"].isna().all()

    def test_bad_customer_id_becomes_na_but_keeps_the_row(self, clean):
        assert clean.loc[clean["order_id"] == 6, "customer_id"].isna().all()

    def test_duplicate_order_id_keeps_the_first(self, clean):
        assert (clean["order_id"] == 2).sum() == 1

    def test_index_is_reset(self, clean):
        assert list(clean.index) == list(range(len(clean)))

    def test_columns_preserved(self, clean):
        assert list(clean.columns) == list(RAW.columns)

    def test_input_is_not_modified(self):
        before = RAW.copy()
        m.clean_orders(RAW)
        pd.testing.assert_frame_equal(RAW, before)

    def test_all_bad_input(self):
        bad = RAW.assign(amount="junk")
        assert len(m.clean_orders(bad)) == 0


class TestRevenueByMonth:
    def test_totals(self, clean):
        got = m.revenue_by_month(clean)
        assert list(got["month"]) == ["2026-01", "2026-02"]
        assert got.loc[0, "revenue"] == pytest.approx(150.5)
        assert got.loc[1, "revenue"] == pytest.approx(200.0)

    def test_counts(self, clean):
        assert list(m.revenue_by_month(clean)["orders"]) == [2, 1]

    def test_columns(self, clean):
        assert list(m.revenue_by_month(clean).columns) == ["month", "revenue", "orders"]

    def test_sorted_and_reset(self, clean):
        got = m.revenue_by_month(clean)
        assert list(got["month"]) == sorted(got["month"])
        assert list(got.index) == list(range(len(got)))

    def test_ignores_non_complete(self, clean):
        # order 6 has an NA status and must not be counted
        assert m.revenue_by_month(clean)["orders"].sum() == 3

    def test_empty_input(self, clean):
        got = m.revenue_by_month(clean.iloc[0:0])
        assert list(got.columns) == ["month", "revenue", "orders"]
        assert len(got) == 0


class TestTopCustomers:
    def test_ranking(self, clean):
        got = m.top_customers(clean, n=2)
        assert list(got["customer_id"]) == [20, 10]
        assert got.loc[0, "total"] == pytest.approx(200.0)

    def test_columns(self, clean):
        assert list(m.top_customers(clean).columns) == ["customer_id", "total", "orders", "avg"]

    def test_average(self, clean):
        got = m.top_customers(clean)
        row = got.loc[got["customer_id"] == 10].iloc[0]
        assert row["avg"] == pytest.approx(75.25)

    def test_respects_n(self, clean):
        assert len(m.top_customers(clean, n=1)) == 1

    def test_n_zero(self, clean):
        got = m.top_customers(clean, n=0)
        assert len(got) == 0
        assert list(got.columns) == ["customer_id", "total", "orders", "avg"]

    def test_index_reset(self, clean):
        assert list(m.top_customers(clean).index) == list(range(len(m.top_customers(clean))))


CUSTOMERS = pd.DataFrame(
    {"customer_id": [10, 20], "name": ["ada", "bob"], "tier": ["gold", "silver"]}
)


class TestEnrichWithCustomers:
    def test_adds_columns(self, clean):
        got = m.enrich_with_customers(clean, CUSTOMERS)
        assert {"name", "tier"} <= set(got.columns)

    def test_row_count_is_unchanged(self, clean):
        assert len(m.enrich_with_customers(clean, CUSTOMERS)) == len(clean)

    def test_matches(self, clean):
        got = m.enrich_with_customers(clean, CUSTOMERS)
        assert got.loc[got["customer_id"] == 10, "name"].eq("ada").all()

    def test_unknown_customers_get_placeholders(self, clean):
        got = m.enrich_with_customers(clean, CUSTOMERS)
        unknown = got.loc[got["customer_id"].isna()]
        assert unknown["name"].eq("unknown").all()
        assert unknown["tier"].eq("none").all()

    def test_duplicate_customers_raise_valueerror(self, clean):
        duplicated = pd.concat([CUSTOMERS, CUSTOMERS], ignore_index=True)
        with pytest.raises(ValueError):
            m.enrich_with_customers(clean, duplicated)

    def test_does_not_leak_pandas_exceptions(self, clean):
        duplicated = pd.concat([CUSTOMERS, CUSTOMERS], ignore_index=True)
        try:
            m.enrich_with_customers(clean, duplicated)
        except Exception as exc:
            assert not isinstance(exc, pd.errors.MergeError)

    def test_order_preserved(self, clean):
        got = m.enrich_with_customers(clean, CUSTOMERS)
        assert list(got["order_id"]) == list(clean["order_id"])


class TestAddRunningTotal:
    def test_adds_the_column(self, clean):
        assert "running_total" in m.add_running_total(clean).columns

    def test_cumulative_per_customer(self, clean):
        got = m.add_running_total(clean).set_index("order_id")["running_total"]
        assert got[1] == pytest.approx(100.0)
        assert got[2] == pytest.approx(150.5)  # same customer, later
        assert got[3] == pytest.approx(200.0)  # a different customer starts again

    def test_row_order_is_preserved(self, clean):
        got = m.add_running_total(clean)
        assert list(got["order_id"]) == list(clean["order_id"])

    def test_input_not_modified(self, clean):
        before = clean.copy()
        m.add_running_total(clean)
        pd.testing.assert_frame_equal(clean, before)

    def test_scales(self):
        rng = np.random.default_rng(0)
        n = 300_000
        big = pd.DataFrame(
            {
                "order_id": range(n),
                "customer_id": rng.integers(0, 1000, n),
                "amount": rng.random(n),
                "ts": pd.date_range("2026-01-01", periods=n, freq="1min", tz="UTC"),
                "status": "complete",
                "region": "north",
            }
        )
        start = time.perf_counter()
        m.add_running_total(big)
        assert time.perf_counter() - start < 3.0  # a row loop takes minutes


class TestPivotRegionMonth:
    def test_shape_and_values(self, clean):
        got = m.pivot_region_month(clean)
        assert list(got.index) == ["north", "south"]
        assert list(got.columns) == ["2026-01", "2026-02"]
        assert got.loc["north", "2026-01"] == pytest.approx(150.5)

    def test_missing_combinations_are_zero(self, clean):
        assert m.pivot_region_month(clean).loc["north", "2026-02"] == 0.0

    def test_columns_axis_has_no_name(self, clean):
        assert m.pivot_region_month(clean).columns.name is None

    def test_sorted(self, clean):
        got = m.pivot_region_month(clean)
        assert list(got.index) == sorted(got.index)
        assert list(got.columns) == sorted(got.columns)


class TestFlagAnomalies:
    @pytest.fixture
    def frame(self):
        return pd.DataFrame(
            {
                "order_id": range(1, 8),
                "customer_id": [1] * 7,
                "amount": [10.0, 12.0, 11.0, 9.0, 500.0, 20.0, 21.0],
                "region": ["north"] * 5 + ["south"] * 2,
                "status": "complete",
                "ts": pd.date_range("2026-01-01", periods=7, tz="UTC"),
            }
        )

    def test_adds_columns(self, frame):
        got = m.flag_anomalies(frame)
        assert {"region_mean", "is_anomaly"} <= set(got.columns)

    def test_flags_the_outlier(self, frame):
        got = m.flag_anomalies(frame, n_std=1.0)
        assert got.loc[got["amount"] == 500.0, "is_anomaly"].all()

    def test_normal_rows_are_not_flagged(self, frame):
        got = m.flag_anomalies(frame, n_std=1.0)
        assert not got.loc[got["amount"] == 10.0, "is_anomaly"].any()

    def test_region_mean_is_per_region(self, frame):
        got = m.flag_anomalies(frame)
        north = got.loc[got["region"] == "north", "region_mean"].unique()
        south = got.loc[got["region"] == "south", "region_mean"].unique()
        assert len(north) == 1 and len(south) == 1
        assert north[0] != south[0]

    def test_region_mean_is_broadcast_not_aggregated(self, frame):
        assert len(m.flag_anomalies(frame)) == len(frame)

    def test_single_row_region_is_never_an_anomaly(self):
        frame = pd.DataFrame({"amount": [10.0, 999.0], "region": ["a", "b"]})
        got = m.flag_anomalies(frame)
        assert not got["is_anomaly"].any()

    def test_is_anomaly_is_boolean(self, frame):
        assert m.flag_anomalies(frame)["is_anomaly"].dtype == bool

    def test_input_not_modified(self, frame):
        before = frame.copy()
        m.flag_anomalies(frame)
        pd.testing.assert_frame_equal(frame, before)

    def test_row_order_preserved(self, frame):
        assert list(m.flag_anomalies(frame)["order_id"]) == list(frame["order_id"])
