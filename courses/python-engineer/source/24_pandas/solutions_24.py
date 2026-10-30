"""Module 24 — reference solutions."""

from __future__ import annotations

import pandas as pd

RAW_COLUMNS = ["order_id", "customer_id", "ts", "amount", "status", "region"]
STATUSES = ["complete", "pending", "cancelled"]


def clean_orders(raw: pd.DataFrame) -> pd.DataFrame:
    return (
        raw.assign(
            order_id=lambda d: pd.to_numeric(d["order_id"], errors="coerce").astype("Int64"),
            customer_id=lambda d: pd.to_numeric(d["customer_id"], errors="coerce").astype("Int64"),
            amount=lambda d: pd.to_numeric(d["amount"], errors="coerce"),
            # An explicit format is ~10x faster and stops pandas guessing per chunk.
            ts=lambda d: pd.to_datetime(
                d["ts"], format="%Y-%m-%d %H:%M:%S", utc=True, errors="coerce"
            ),
            # NA-out the unknown values FIRST: constructing a Categorical from values
            # outside its categories is deprecated (Pandas4Warning) and will raise.
            status=lambda d: d["status"]
            .where(d["status"].isin(STATUSES))
            .astype(pd.CategoricalDtype(STATUSES)),
            region=lambda d: d["region"].str.strip().str.lower(),
        )
        .dropna(subset=["order_id", "ts", "amount"])
        .loc[lambda d: d["amount"] >= 0]
        .drop_duplicates(subset="order_id", keep="first")
        .reset_index(drop=True)
        .loc[:, list(raw.columns)]
    )


def revenue_by_month(orders: pd.DataFrame) -> pd.DataFrame:
    empty = pd.DataFrame(
        {"month": pd.Series(dtype="str"), "revenue": pd.Series(dtype="float64"),
         "orders": pd.Series(dtype="int64")}
    )  # fmt: skip
    completed = orders.loc[lambda d: d["status"] == "complete"]
    if completed.empty:
        return empty

    return (
        completed
        # strftime, not to_period: to_period drops the timezone and warns.
        .assign(month=lambda d: d["ts"].dt.strftime("%Y-%m"))
        .groupby("month", as_index=False, observed=True)
        .agg(revenue=("amount", "sum"), orders=("order_id", "size"))
        .sort_values("month")
        .reset_index(drop=True)
    )


def top_customers(orders: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    columns = ["customer_id", "total", "orders", "avg"]
    completed = orders.loc[lambda d: d["status"] == "complete"]
    if n <= 0 or completed.empty:
        return pd.DataFrame({c: pd.Series(dtype="float64") for c in columns})

    return (
        completed.groupby("customer_id", as_index=False, observed=True)
        .agg(total=("amount", "sum"), orders=("order_id", "size"))
        .assign(avg=lambda d: (d["total"] / d["orders"]).round(2))
        .sort_values(["total", "customer_id"], ascending=[False, True])
        .head(n)
        .reset_index(drop=True)
        .loc[:, columns]
    )


def enrich_with_customers(orders: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    try:
        merged = pd.merge(
            orders,
            customers[["customer_id", "name", "tier"]],
            on="customer_id",
            how="left",
            validate="many_to_one",  # a duplicate key raises instead of exploding rows
        )
    except pd.errors.MergeError as exc:
        raise ValueError(f"customers must be unique per customer_id: {exc}") from exc

    return merged.assign(
        name=lambda d: d["name"].fillna("unknown"),
        tier=lambda d: d["tier"].fillna("none"),
    )


def add_running_total(orders: pd.DataFrame) -> pd.DataFrame:
    return (
        orders.sort_values("ts", kind="stable")
        .assign(running_total=lambda d: d.groupby("customer_id", observed=True)["amount"].cumsum())
        .sort_index()  # restore the caller's row order
    )


def pivot_region_month(orders: pd.DataFrame) -> pd.DataFrame:
    return (
        orders.loc[lambda d: d["status"] == "complete"]
        .assign(month=lambda d: d["ts"].dt.strftime("%Y-%m"))
        .pivot_table(
            index="region", columns="month", values="amount", aggfunc="sum", fill_value=0.0
        )
        .sort_index()
        .sort_index(axis=1)
        .rename_axis(columns=None)  # otherwise the columns index is named "month"
    )


def flag_anomalies(orders: pd.DataFrame, n_std: float = 2.0) -> pd.DataFrame:
    grouped = orders.groupby("region", observed=True)["amount"]
    return orders.assign(
        # transform, not agg: we need one value per ROW, not per group.
        region_mean=grouped.transform("mean"),
        region_std=grouped.transform("std"),  # pandas' std is ddof=1 already
    ).assign(
        is_anomaly=lambda d: (d["amount"] > d["region_mean"] + n_std * d["region_std"]).fillna(
            False
        )
    ).drop(columns="region_std")
