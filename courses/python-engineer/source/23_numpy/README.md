# 23 — NumPy

NumPy is not "a library for maths". It's a different **execution model**: you stop writing
loops and start describing operations over whole arrays, which run in C. Everything in
scientific Python — pandas, scikit-learn, PyTorch, polars' interop — sits on this model.

If you did project 02 (`tensorlab`), this is the same idea, done properly — and this is
the backend you'd swap in for milestone 6.

## In plain English

A Python list of a million numbers is a million *separate objects*, each individually
wrapped, scattered across memory, each with its own bookkeeping. Think of a box of sweets
where every single sweet has its own wrapper, box and address label.

A NumPy array is a **tube** — one label, one block of memory, all the same type, packed
end to end. That's it, and it's why NumPy is fast: the computer can rip through a tightly
packed block at full speed, whereas chasing a million scattered objects is mostly waiting.

The mental shift is that you stop writing loops. Instead of "for each number, multiply it by
two", you write `array * 2` and let the fast C code underneath do all million at once. This
feels strange for about a day and then feels obvious.

**Broadcasting** is the other big idea: when you combine arrays of different shapes, NumPy
stretches the smaller one to fit, without actually copying it. Add a row of 4 numbers to a
3×4 grid and it adds that row to *every* row. Enormously convenient, and worth learning
properly because it's how you avoid loops in real code.

**Watch out for:** slicing an array gives you a **window onto the original**, not a copy.
Change the slice and you've changed the original — which is either exactly what you wanted
or a very confusing afternoon. The lesson shows when you get a window and when you get a
copy, because the rules are not obvious.

## 1. The `ndarray`

A contiguous block of memory plus metadata: `dtype`, `shape`, `strides`.

```python
a = np.array([[1, 2, 3], [4, 5, 6]])
a.shape      # (2, 3)
a.ndim       # 2
a.size       # 6
a.dtype      # dtype('int64')
a.strides    # (24, 8) — bytes to step to the next row / next column
a.nbytes     # 48
```

That's why it's fast: **one type, one block, no per-element Python objects.** A
`list[int]` of a million values is a million pointers to a million 28-byte objects;
`np.arange(1_000_000)` is 8 MB of ints.

Creation: `np.array`, `zeros`, `ones`, `full`, `empty` (uninitialised — garbage, not zeros),
`arange`, `linspace`, `eye`, `zeros_like`, `random.default_rng().normal(...)`.

## 2. dtypes, and the traps in them

```python
np.array([1, 2, 3])            # int64  (int32 on Windows — always be explicit)
np.array([1, 2, 3], dtype=np.float32)
a.astype(np.float64)           # returns a COPY
```

- **Integer overflow wraps silently.** `np.int8(127) + 1 == -128`. NumPy 2.0 raises on
  out-of-range *scalar* conversion, but arithmetic still wraps.
- `float32` has ~7 decimal digits. Sums over big float32 arrays lose precision; use
  `dtype=np.float64` for accumulation, or `np.sum(a, dtype=np.float64)`.
- `nan != nan`. Use `np.isnan`, `np.nansum`, `np.allclose(..., equal_nan=True)`.
- `object` dtype means "back to Python speed" — usually a mistake you made by accident.

## 3. Vectorisation

```python
result = np.sqrt(a**2 + b**2)          # one pass in C
result = [math.sqrt(x*x + y*y) for x, y in zip(a, b)]   # one Python call per element
```

Every arithmetic operator, comparison and `np.*` function is a **ufunc**: element-wise,
typed, looped in C, with optional `out=` to avoid allocation.

The rule: **if you wrote a `for` loop over array elements, you left a large multiple on
the table.** How large is workload-specific — the lesson file measures ~10–30× for this
expression, and it *shrinks* at large sizes because the temporaries make it
memory-bandwidth-bound. Quote your own measurements, not a number off a blog.

`np.vectorize` is *not* a fix — it's a convenience wrapper around a Python loop, and the
lesson shows it being slower than the loop it replaces.

## 4. Broadcasting

Two arrays are compatible when, comparing shapes **right to left**, each pair of
dimensions is equal, or one of them is 1 (or missing).

```
(3, 4) + (4,)      -> (3, 4)      row vector added to every row
(3, 4) + (3, 1)    -> (3, 4)      column vector added to every column
(3, 4) + (3,)      -> ERROR       4 vs 3
```

`a[:, None]` (or `np.newaxis`) inserts an axis — the standard way to make a column vector
so broadcasting does what you want:

```python
distances = np.sqrt(((a[:, None, :] - b[None, :, :]) ** 2).sum(axis=-1))   # all pairs, no loop
```

Broadcasting doesn't copy — it iterates with a stride of 0. But the **result** is
materialised, so `a[:, None, :] - b[None, :, :]` on 10k×10k allocates 800 GB. Watch the
output shape, not the inputs.

## 5. Indexing: views vs copies

| Form | Gives you |
|---|---|
| `a[1:3, ::2]` — basic slicing | a **VIEW**: writing to it writes to `a` |
| `a[[0, 2, 4]]` — fancy indexing | a **COPY** |
| `a[a > 5]` — boolean mask | a **COPY** |
| `a.reshape(...)`, `.T`, `.ravel()` | a view when it can be, a copy when it can't |
| `a.flatten()`, `.copy()` | always a copy |

```python
np.shares_memory(a, b)      # the definitive answer
```

This is the #1 source of NumPy bugs: you slice, mutate, and silently change the original —
or you slice, mutate, and *don't*, because it was fancy indexing.

Assignment through a view *does* write back: `a[a > 5] = 0` works, because it's
`__setitem__`, not `__getitem__`.

## 6. Axes and reductions

`axis=k` means "**collapse** axis k".

```python
a.shape                  # (rows, cols) = (3, 4)
a.sum(axis=0).shape      # (4,)  — summed down the rows, one value per column
a.sum(axis=1).shape      # (3,)  — summed across the columns, one value per row
a.sum(axis=1, keepdims=True).shape   # (3, 1) — keeps it broadcastable
```

`keepdims=True` is what lets `a / a.sum(axis=1, keepdims=True)` normalise rows.

Reductions: `sum mean std var min max prod any all argmin argmax cumsum cumprod`,
plus the NaN-skipping `nan*` family, and `np.median`/`np.percentile`.

## 7. The functions worth memorising

| Function | Use |
|---|---|
| `np.where(cond, a, b)` | vectorised ternary |
| `np.clip(a, lo, hi)` | bound values |
| `np.unique(a, return_counts=True)` | distinct values + frequencies |
| `np.argsort`, `np.argpartition` | indices; `argpartition` is O(n) for top-k |
| `np.concatenate`, `stack`, `vstack`, `hstack`, `split` | joining and splitting |
| `np.einsum("ij,jk->ik", a, b)` | any contraction, explicitly |
| `a @ b`, `np.dot`, `np.linalg.solve/inv/eig/norm` | linear algebra (BLAS/LAPACK) |
| `np.isnan`, `np.isfinite`, `np.allclose` | float sanity |
| `np.lib.stride_tricks.sliding_window_view` | windows with no copy |
| `rng = np.random.default_rng(seed)` | **the** modern RNG API |

Use `default_rng(seed)`, not `np.random.seed()` — the legacy global RNG is shared mutable
state, which is exactly what module 09 told you to avoid.

## 8. Performance notes

- Preallocate and write into `out=`; repeated `np.append` reallocates every call (it's the
  `list.insert(0, x)` of NumPy).
- `a.T` is a free view with swapped strides. Element-wise work on it is barely slower;
  what costs is **materialising** it in a new layout (`np.ascontiguousarray` was ~2.5×
  a plain copy when measured). Measure before you "fix" a layout.
- In-place ops (`a += b`, `np.add(a, b, out=a)`) avoid a temporary allocation.
- The intermediate arrays in `((a - b) ** 2).sum()` are real allocations — for big data,
  `np.einsum` or chunking avoids them.
- NumPy releases the GIL for most heavy operations, so threads *do* parallelise it
  (module 10).
- **Speed can cost accuracy.** Computing pairwise distances as
  `|x|² + |y|² − 2x·y` avoids a huge intermediate array, but it subtracts nearly equal
  numbers, so small distances carry ~`sqrt(eps)` ≈ 1e-7 of error — and the exact amount
  depends on which BLAS library is installed. This course's own CI caught it: a test
  asserting 1e-8 passed locally and failed on GitHub's runners. Choose the fast form
  deliberately, and write tolerances that reflect what it actually delivers.

## Exercises

`exercises_23.py`, then `pytest 23_numpy`. Several tests time large inputs, so a Python
loop over elements will fail even when it's correct.

## Further reading

- [NumPy user guide](https://numpy.org/doc/stable/user/) — especially "broadcasting" and "copies and views"
- [NumPy 2.0 migration guide](https://numpy.org/doc/stable/numpy_2_0_migration_guide.html)
