"""Module 24 exercises.  pytest 24_pandas

Rules for this module:
- No `iterrows`, `itertuples` or `apply(axis=1)`. Two tests time large frames and will
  fail a row loop even when it returns the right answer.
- Never mutate an input frame. Under pandas 3.0's copy-on-write you mostly can't by
  accident — but you can still do it deliberately, and the tests check.
- Prefer the chaining style: `.loc[lambda d: ...]`, `.assign(...)`, `.pipe(...)`.
"""

from __future__ import annotations

import pandas as pd

# The raw shape the exercises receive: everything is text, some of it is junk.
RAW_COLUMNS = ["order_id", "customer_id", "ts", "amount", "status", "region"]


def clean_orders(raw: pd.DataFrame) -> pd.DataFrame:
    """Turn a frame of strings into a typed, validated one.

    Input columns are all text: order_id, customer_id, ts, amount, status, region.

    Output requirements:
    - `order_id`, `customer_id` -> `Int64` (nullable — junk becomes NA, it does not raise)
    - `amount` -> `float64`, via `pd.to_numeric(..., errors="coerce")`
    - `ts` -> `datetime64[ns, UTC]`, parsed with an explicit `format="%Y-%m-%d %H:%M:%S"`
      and `utc=True`; unparsable values become NaT
    - `status` -> `category` with exactly the categories
      ["complete", "pending", "cancelled"]; any other value becomes NA. Note: you must
      NA-out the unknown values *before* casting — building a Categorical from values
      outside its own categories is deprecated and raises a Pandas4Warning.
    - `region` -> stripped and lowercased text
    - Rows with NA in `order_id`, `ts` or `amount` are DROPPED (they're unusable)
    - Rows with a negative `amount` are dropped
    - Duplicate `order_id` keeps the FIRST occurrence
    - The index is reset to 0..n-1
    - Column order is preserved

    The input frame must come back unmodified.
    """
    raise NotImplementedError


def revenue_by_month(orders: pd.DataFrame) -> pd.DataFrame:
    """Monthly revenue over completed orders only.

    Returns a frame with columns `["month", "revenue", "orders"]`:
    - `month` is a string "YYYY-MM" (use `.dt.strftime`, not `to_period` — that drops
      the timezone and warns)
    - `revenue` is the summed `amount` as float
    - `orders` is the row count as int
    - sorted by month ascending, index reset
    - months with no completed orders simply don't appear
    - an empty input gives an empty frame WITH those three columns and the right dtypes
    """
    raise NotImplementedError


def top_customers(orders: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    """The n biggest customers by total completed spend.

    Returns `["customer_id", "total", "orders", "avg"]`:
    - `total` summed amount, `orders` the count, `avg` = total / orders rounded to 2dp
    - sorted by total descending, ties broken by customer_id ascending
    - at most n rows; `n <= 0` gives an empty frame with those columns
    - index reset

    One `groupby(...).agg(...)` with named aggregation, then sort and head. No loop.
    """
    raise NotImplementedError


def enrich_with_customers(orders: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    """Left-join customer `name` and `tier` onto orders, safely.

    - `customers` has `customer_id`, `name`, `tier`.
    - Pass `validate="many_to_one"` so a duplicated customer_id RAISES instead of
      silently multiplying your rows. That single keyword is the whole point of this
      exercise.
    - Orders whose customer is unknown are kept, with `name` = "unknown" and
      `tier` = "none".
    - Row count and order are unchanged from `orders`.
    - Raise `ValueError` if `customers` has duplicate ids (catch pandas' MergeError and
      re-raise as ValueError, so callers don't have to know you used pandas).
    """
    raise NotImplementedError


def add_running_total(orders: pd.DataFrame) -> pd.DataFrame:
    """Add a per-customer running total of `amount`, ordered by time.

    Returns a copy with one extra column `running_total` (float):
    - within each `customer_id`, the cumulative sum of `amount` ordered by `ts`
    - the ORIGINAL row order is preserved — sort, compute, then restore
    - the input is not modified

    `groupby(...)["amount"].cumsum()` on a time-sorted frame does it. The trap is
    returning the rows in sorted order instead of the original order; the tests check.
    """
    raise NotImplementedError


def pivot_region_month(orders: pd.DataFrame) -> pd.DataFrame:
    """Revenue by region (rows) and month (columns), completed orders only.

    - index: `region`, sorted ascending
    - columns: "YYYY-MM" strings, sorted ascending
    - values: summed amount, missing combinations filled with 0.0
    - the columns index has no name (call `.rename_axis(columns=None)`) — pandas leaves
      "month" there otherwise and it breaks frame comparisons
    """
    raise NotImplementedError


def flag_anomalies(orders: pd.DataFrame, n_std: float = 2.0) -> pd.DataFrame:
    """Flag orders far above their own region's average.

    Returns a copy with two extra columns:
    - `region_mean`: the mean `amount` of that row's region (`transform`, not `agg` —
      you need it broadcast back to every row)
    - `is_anomaly`: True when `amount > region_mean + n_std * region_std`, where
      region_std is the SAMPLE std (ddof=1) of that region

    - A region with fewer than 2 rows has an NA std; those rows are never anomalies.
    - Row order and the input frame are untouched.
    """
    raise NotImplementedError
