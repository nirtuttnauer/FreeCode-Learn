"""Module 24 — runnable lesson. `python 24_pandas/lesson_24.py`"""

from __future__ import annotations

import time
import warnings

import numpy as np
import pandas as pd

INTRO = """A spreadsheet you drive with code. Every row has a label, and pandas lines tables up BY
LABEL — powerful, and the reason mismatched data silently turns into blanks instead of an
error. This runs on pandas 3.0, where some long-standing behaviour changed."""

rng = np.random.default_rng(7)


def make_orders(n: int = 12) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order_id": range(1, n + 1),
            "customer_id": rng.integers(1, 4, size=n),
            "region": rng.choice(["north", "south"], size=n),
            "amount": rng.integers(10, 500, size=n).astype(float),
            "ts": pd.date_range("2026-01-01", periods=n, freq="9D", tz="UTC"),
            "status": rng.choice(["complete", "pending", "cancelled"], size=n),
        }
    )


def structures() -> None:
    print(f"\n== pandas {pd.__version__} ==")
    a = pd.Series([1, 2, 3], index=["x", "y", "z"])
    b = pd.Series([10, 20], index=["y", "z"])
    print("  alignment happens by LABEL, not position:")
    for line in (a + b).to_string().splitlines():
        print(f"    {line}")
    print("  a missing label becomes NaN rather than an error — the classic silent bug")

    df = make_orders(4)
    print(f"\n  dtypes:\n    {df.dtypes.to_dict()}")
    print("  note: text columns are the new `str` dtype in 3.0, not `object`")


def copy_on_write() -> None:
    print("\n== copy-on-write (the 3.0 default) ==")
    df = make_orders(6)
    df["flagged"] = False

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df[df["amount"] > 100]["flagged"] = True  # a write to a temporary
    print(f"  chained assignment set {df['flagged'].sum()} rows  <- it did NOTHING")
    warned = caught[0].category.__name__ if caught else "nothing"
    print(f"  and pandas 3.0 raises a {warned} to tell you so")

    df.loc[df["amount"] > 100, "flagged"] = True
    print(f"  .loc[mask, col] = value set {df['flagged'].sum()} rows  <- correct")

    original = make_orders(3)
    subset = original[["amount"]]
    subset.loc[0, "amount"] = -999
    print(f"\n  writing to a subset no longer touches the parent: {original.loc[0, 'amount']}")
    print("  that's CoW: no SettingWithCopyWarning, and no action at a distance either")


def selecting() -> None:
    print("\n== selecting ==")
    df = make_orders(8)
    print(f"  .loc is label-based and END-INCLUSIVE: {len(df.loc[0:3])} rows")
    print(f"  .iloc is positional and end-exclusive:  {len(df.iloc[0:3])} rows")

    mask = (df["amount"] > 100) & (df["status"] == "complete")
    print(f"\n  boolean mask: {mask.sum()} of {len(df)} rows")
    print(f"  .query(): {len(df.query('amount > 100 and status == \"complete\"'))} rows")

    try:
        df["amount"] > 100 and df["status"] == "complete"
    except ValueError as exc:
        print(f"  `and` on a Series raises: {str(exc)[:60]}...")
    print("  use & | ~ — and parenthesise, they bind tighter than comparisons")


def dtypes_and_missing() -> None:
    print("\n== dtypes and missing data ==")
    raw = pd.DataFrame({"id": ["1", "2", "oops"], "amount": ["10.5", "", "30"]})
    clean = raw.assign(
        id=lambda d: pd.to_numeric(d["id"], errors="coerce").astype("Int64"),
        amount=lambda d: pd.to_numeric(d["amount"], errors="coerce"),
    )
    print(f"  errors='coerce' turns junk into NA:\n{clean.to_string(index=False)}")
    print(f"  Int64 (capital I) holds NA; int64 cannot: {clean['id'].dtype}")
    print(f"\n  missing per column: {clean.isna().sum().to_dict()}")

    labels = pd.Series(["north", "south"] * 50_000)
    print(f"\n  50k repeated strings as str:      {labels.memory_usage(deep=True):>9,} bytes")
    print(f"  the same as category:             {labels.astype('category').memory_usage(deep=True):>9,} bytes")


def grouping() -> None:
    print("\n== groupby: agg vs transform ==")
    df = make_orders(12)

    summary = df.groupby("region", as_index=False).agg(
        orders=("order_id", "size"),
        revenue=("amount", "sum"),
        biggest=("amount", "max"),
    )
    print(f"  named aggregation -> one row per group:\n{summary.to_string(index=False)}")

    with_share = df.assign(
        region_total=lambda d: d.groupby("region")["amount"].transform("sum"),
        share=lambda d: (d["amount"] / d["region_total"]).round(3),
    )
    print(f"\n  transform broadcasts back to every row:\n{with_share[['region', 'amount', 'share']].head(4).to_string(index=False)}")
    print("  agg -> one row per group. transform -> original shape. apply -> slow, last resort.")


def joining() -> None:
    print("\n== merging, and why validate= matters ==")
    orders = pd.DataFrame({"order_id": [1, 2, 3], "customer_id": [10, 20, 99]})
    customers = pd.DataFrame({"customer_id": [10, 20], "name": ["ada", "bob"]})

    merged = pd.merge(orders, customers, on="customer_id", how="left",
                      validate="many_to_one", indicator=True)
    print(merged.to_string(index=False))
    print(f"  unmatched rows: {(merged['_merge'] == 'left_only').sum()}")

    duplicated = pd.concat([customers, customers])
    try:
        pd.merge(orders, duplicated, on="customer_id", validate="many_to_one")
    except pd.errors.MergeError as exc:
        print(f"\n  validate= caught a duplicate key: {exc}")
    print(f"  without it you'd silently get {len(pd.merge(orders, duplicated, on='customer_id'))} rows from 3")


def reshaping_and_time() -> None:
    print("\n== reshaping and time series ==")
    df = make_orders(20)

    pivot = df.pivot_table(index="region", columns="status", values="amount",
                           aggfunc="sum", fill_value=0)
    print(f"  pivot_table:\n{pivot.to_string()}")

    monthly = (
        df.set_index("ts")
        .resample("1ME")["amount"]
        .sum()
        .rename("revenue")
    )
    print(f"\n  resampled to month end:\n{monthly.head(3).to_string()}")

    rolling = df.sort_values("ts").assign(
        rolling_3=lambda d: d["amount"].rolling(3, min_periods=1).mean().round(1)
    )
    print(f"\n  rolling mean:\n{rolling[['ts', 'amount', 'rolling_3']].head(4).to_string(index=False)}")


def performance() -> None:
    print("\n== vectorise, don't iterate ==")
    n = 200_000
    df = pd.DataFrame({"a": rng.random(n), "b": rng.random(n)})

    start = time.perf_counter()
    [row.a * row.b for row in df.head(20_000).itertuples()]
    iter_time = (time.perf_counter() - start) * 10  # scale to n

    start = time.perf_counter()
    df["a"] * df["b"]
    vec_time = time.perf_counter() - start

    print(f"  itertuples (extrapolated to {n:,}): {iter_time * 1000:>8.1f} ms")
    print(f"  vectorised column product:          {vec_time * 1000:>8.1f} ms")
    print(f"  -> ~{iter_time / vec_time:.0f}x")

    start = time.perf_counter()
    df.head(20_000).apply(lambda r: "hi" if r.a > 0.5 else "lo", axis=1)
    apply_time = (time.perf_counter() - start) * 10
    start = time.perf_counter()
    np.where(df["a"] > 0.5, "hi", "lo")
    where_time = time.perf_counter() - start
    print(f"\n  apply(axis=1) (extrapolated):       {apply_time * 1000:>8.1f} ms")
    print(f"  np.where:                           {where_time * 1000:>8.1f} ms")
    print(f"  -> ~{apply_time / where_time:.0f}x")


def chaining() -> None:
    print("\n== the chaining style ==")
    orders = make_orders(30)
    result = (
        orders
        .loc[lambda d: d["status"].eq("complete")]
        .assign(month=lambda d: d["ts"].dt.strftime("%Y-%m"))  # not to_period: it drops the tz
        .groupby("month", as_index=False)
        .agg(revenue=("amount", "sum"), orders=("order_id", "size"))
        .sort_values("month")
    )
    print(result.to_string(index=False))
    print("  one expression, no df2/df_clean/df_final, nothing half-mutated")


if __name__ == "__main__":
    print(INTRO)
    structures()
    copy_on_write()
    selecting()
    dtypes_and_missing()
    grouping()
    joining()
    reshaping_and_time()
    performance()
    chaining()
