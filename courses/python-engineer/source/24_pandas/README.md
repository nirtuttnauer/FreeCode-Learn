# 24 — pandas

pandas is a query engine with a Python API. The skill isn't memorising methods — it's
learning to express a whole transformation as **vectorised operations over columns**
instead of a loop over rows.

This module targets **pandas 3.0**, which changed two defaults that most tutorials on the
internet predate. Read §2 before anything else.

## In plain English

pandas is a spreadsheet you drive with code. A `DataFrame` is a table — columns with names,
rows of data — and you transform it with operations on whole columns instead of clicking
cells.

The thing that makes it different from a spreadsheet is the **index**: every row has a
label, and when you combine two tables pandas lines them up *by label*, not by position.
That's powerful and it's the source of the classic confusion — combining two things whose
labels don't match gives you a table full of blanks rather than an error.

The other habit worth building early is **vectorised thinking**, same as NumPy. Writing a
loop over rows is the natural instinct and it is roughly 75× slower than doing the whole
column at once — and for a conditional, over 1000× slower. The lesson measures both.

One note on version: this course runs on **pandas 3.0**, which changed a long-standing
behaviour. Most tutorials online predate it. In particular, `df[mask]["col"] = value` now
silently does *nothing* (it writes to a temporary copy). The correct form is
`df.loc[mask, "col"] = value`. Worth reading section 2 before you copy anything off the
internet.

**Watch out for:** merging two tables when the right-hand one has duplicate keys — you
quietly get *more rows than you started with*. Passing `validate="many_to_one"` turns that
silent disaster into an immediate error.

## 1. Series and DataFrame

- **Series**: a typed 1-D array (NumPy or Arrow underneath) **plus an index**.
- **DataFrame**: an ordered dict of Series sharing one index.

The **index** is the thing that makes pandas different from a spreadsheet: it aligns data
automatically in every binary operation.

```python
a = pd.Series([1, 2, 3], index=["x", "y", "z"])
b = pd.Series([10, 20], index=["y", "z"])
a + b        # x NaN, y 12, z 23  — aligned by LABEL, not position
```

That alignment is a feature and a trap: a botched index silently produces NaNs rather than
an error. `.reset_index(drop=True)` when you don't want it.

## 2. What changed in pandas 3.0

**Copy-on-Write is now the only behaviour.** Every operation behaves as if it returned a
copy; a write never propagates to a parent object. This kills `SettingWithCopyWarning` and
the entire class of "did that assignment land?" bugs.

The practical consequence — **chained assignment silently does nothing**:

```python
df[df["amount"] > 100]["flagged"] = True    # NO-OP. Writes to a temporary.
df.loc[df["amount"] > 100, "flagged"] = True   # correct
```

Also: `inplace=True` no longer avoids a copy. It has no performance benefit and hurts
readability — stop using it and chain instead.

**Strings default to a real `str` dtype**, not `object`. Columns of text are now
Arrow-backed: less memory, much faster string operations, and `NaN` in a string column is
`NA` rather than a float.

## 3. Selecting

```python
df["col"]                 # a Series
df[["a", "b"]]            # a DataFrame
df.loc[rows, cols]        # LABEL based, end-INCLUSIVE
df.iloc[rows, cols]       # POSITION based, end-exclusive
df.at[label, "col"]       # single scalar, fast
df.query("amount > 100 and status == 'ok'")
```

Boolean masks are the workhorse:

```python
df[(df["amount"] > 100) & (df["status"] == "ok")]      # & | ~ , and MIND THE PARENTHESES
df[df["status"].isin(["ok", "pending"])]
df[df["email"].str.contains("@example", na=False)]
df[df["amount"].between(10, 100)]
```

`and`/`or` raise on Series — use `&`/`|`, and parenthesise because they bind tighter than
comparison.

## 4. dtypes

| dtype | Use |
|---|---|
| `int64` / `float64` | numbers; `int64` cannot hold NA |
| `Int64` (capital I) | **nullable** integer — an int column with missing values |
| `str` | text (Arrow-backed in 3.0) |
| `category` | low-cardinality labels — big memory and groupby wins |
| `datetime64[ns, tz]` | timestamps; keep them tz-aware (module 19) |
| `bool` / `boolean` | non-nullable / nullable |

`df.dtypes`, `df.info(memory_usage="deep")`, `df.astype({"id": "Int64"})`,
`pd.to_numeric(s, errors="coerce")`, `pd.to_datetime(s, format=..., utc=True)`.

**Always pass `format=`** to `to_datetime` on a known format — it's an order of magnitude
faster and it stops pandas guessing differently on different chunks.

## 5. Missing data

`NaN` (float), `NaT` (datetime), `pd.NA` (the nullable ones). All are "missing", and none
compare equal to themselves.

```python
df.isna().sum()                 # missing per column — the first thing to run on new data
df.dropna(subset=["email"])
df["amount"].fillna(0)
df["amount"].ffill()            # careful: propagates stale values forward
```

## 6. groupby: split → apply → combine

```python
df.groupby("dept")["salary"].mean()
df.groupby(["dept", "level"]).agg(
    headcount=("id", "size"),
    total_pay=("salary", "sum"),
    top_pay=("salary", "max"),
)                                        # named aggregation: flat, readable columns
df.groupby("dept")["salary"].transform("mean")   # broadcast BACK to the original rows
df.groupby("dept").filter(lambda g: len(g) > 5)
```

Know the difference:
- `agg` → one row per group.
- `transform` → same shape as the input (for "salary minus department mean").
- `apply` → arbitrary, and **slow**: it runs Python per group. Last resort.

`observed=True` for categorical keys (otherwise you get the full cartesian product),
`dropna=False` to keep NA keys, `as_index=False` to get a flat frame back.

## 7. Joining

```python
pd.merge(orders, customers, on="customer_id", how="left",
         validate="many_to_one", indicator=True)
pd.concat([df1, df2], ignore_index=True)      # stack rows
df.join(other)                                 # index-based, convenience wrapper
```

**Always pass `validate=`.** `"many_to_one"`, `"one_to_one"` etc. turn a silent row
explosion — the classic "why do I have 4 million rows now?" — into an immediate error.
`indicator=True` adds a `_merge` column so you can count what didn't match.

## 8. Reshaping and time series

```python
df.pivot_table(index="region", columns="month", values="sales", aggfunc="sum", fill_value=0)
df.melt(id_vars="id", var_name="metric", value_name="value")     # wide -> long
df.set_index("ts").resample("1D").sum()                          # time bucketing
df["amount"].rolling(7).mean()                                    # rolling window
df.sort_values("ts").groupby("user")["amount"].cumsum()
```

## 9. Performance

- **Never** `iterrows` / `itertuples` / `apply(axis=1)` in a hot path. They're a Python
  loop with extra allocation. Vectorise, or use `np.where`/`np.select` for conditionals.
- `category` dtype for repeated strings: often 10–100× less memory and much faster groupby.
- Read only what you need: `usecols=`, `dtype=`, `chunksize=` in `read_csv`.
- Parquet over CSV for anything you write yourself — typed, columnar, compressed.
- `dtype_backend="pyarrow"` for lower memory and faster strings.
- If your data doesn't fit or pandas is the bottleneck: **polars** (faster, lazy, saner
  API) or **DuckDB** (SQL over your DataFrames). Both interop through Arrow at zero copy.

## 10. Style: chain, don't mutate

```python
result = (
    orders
    .loc[lambda d: d["status"].eq("complete")]
    .assign(month=lambda d: d["ts"].dt.to_period("M"))
    .groupby("month", as_index=False)
    .agg(revenue=("amount", "sum"))
    .sort_values("month")
)
```

Each step is a pure transformation, the whole thing reads top to bottom, and there are no
half-mutated intermediates named `df2`, `df_clean`, `df_final_v2`.

## Exercises

`exercises_24.py`, then `pytest 24_pandas`.

## Further reading

- [pandas user guide](https://pandas.pydata.org/docs/user_guide/) — "Copy-on-Write" and "group by" especially
- [Effective pandas](https://github.com/mattharrison) (Harrison) for the chaining style
- [polars](https://docs.pola.rs/) when pandas stops being enough
