# 13 — Performance and memory

The rules, in order:

1. **Measure.** Your intuition about where time goes is wrong. Everyone's is.
2. **Fix the algorithm.** O(n²) → O(n) beats every micro-optimisation ever written.
3. **Do less work.** Cache, batch, avoid recomputation, stream instead of materialise.
4. **Then** micro-optimise the hot loop the profiler pointed at.
5. **Then** leave Python (numpy, Cython, Rust, a C extension).

## In plain English

Making a program faster is almost never about clever tricks. It's about **doing less work**.

The rules, in strict order:

1. **Measure.** Not "I think it's slow here" — actually measure. Everyone's intuition about
   this is wrong, including mine, including yours. There's a tool (a *profiler*) that just
   tells you.
2. **Fix the approach, not the code.** If you're searching a list a million times, no amount
   of micro-tuning will save you; switching to a set will, instantly.
3. *Then*, if it still matters, tune the hot loop.

Here's the intuition for why step 2 dominates. Say your program takes n steps for n items.
Fine. Now say it takes n × n steps. At 100 items that's 10,000 — instant, and it looks fine
on your laptop. At 100,000 items it's 10,000,000,000, and your program appears to hang
forever. Nothing about the code changed. The *shape* of the cost did.

That's why every exercise here gives you a working-but-slow function and asks you to make it
fast **without changing what it does** — and the tests measure, so only a real fix passes.

**Watch out for:** two claims in this module that most tutorials get wrong. The lesson
measures both and tells you the truth instead.

## 1. Measuring

```python
timeit.timeit("f(x)", globals=globals(), number=1000)     # micro-benchmarks
python -m timeit -s "setup" "statement"
time.perf_counter()                                        # wall clock, monotonic
time.process_time()                                        # CPU only, excludes sleep
```

Profilers:

```bash
python -m cProfile -s cumtime script.py | head -30    # deterministic, ~2x overhead
python -m cProfile -o out.prof script.py              # then: snakeviz out.prof
py-spy top --pid 1234                                 # sampling; works on LIVE production
py-spy record -o flame.svg -- python script.py        # flame graph, no code changes
```

Line-level: `line_profiler` (`@profile` + `kernprof -l -v`). Memory: `tracemalloc`
(stdlib), `memray` (best-in-class), `memory_profiler`.

Read `cProfile` output as: **`tottime`** = time in the function itself,
**`cumtime`** = including callees. Sort by `tottime` to find the hot function, by
`cumtime` to find the expensive call tree.

## 2. Algorithmic wins (the ones that actually matter)

| Anti-pattern | Cost | Fix |
|---|---|---|
| `x in big_list` in a loop | O(n·m) | build a `set` once |
| `s += chunk` in a loop | O(n²) copies | `"".join(parts)` |
| `list.insert(0, x)` / `pop(0)` | O(n) each | `collections.deque` |
| Repeated `sorted()` in a loop | O(n log n)·m | sort once, or `heapq` |
| Rebuilding a lookup dict per call | O(n) each | build once, pass it in |
| Nested loop over two lists | O(n·m) | join on a dict keyed by the match field |
| Loading a whole file to count lines | O(file) memory | iterate the file object |

## 3. Caching

```python
@functools.cache                  # unbounded — leaks if the key space is unbounded
@functools.lru_cache(maxsize=1024)
@functools.cached_property        # per-instance, computed once
```

Requirements: arguments hashable, function **pure**. Check effectiveness with
`f.cache_info()` — a hit rate near zero means you're paying overhead for nothing.

`@cache` on a method keeps every `self` alive forever. That's a memory leak with a
decorator on top.

## 4. Memory

```python
sys.getsizeof(obj)              # shallow! a list of lists reports only the outer list
tracemalloc.start(); ...; tracemalloc.take_snapshot().statistics("lineno")
```

| Technique | Saves |
|---|---|
| `__slots__` | ~40–50% per instance; no `__dict__` |
| `@dataclass(slots=True)` | same, declaratively |
| generators instead of lists | everything but the current item |
| `array.array` / `numpy` for numbers | 8 bytes vs ~28 per int object |
| `bytes`/`memoryview` for buffers | avoids copies on slicing |
| interning repeated strings (`sys.intern`) | one copy of each key |

Python objects are *fat*: an `int` is ~28 bytes, an empty `dict` ~64, an empty `list` ~56.
A million-row list of dataclasses is not a "small" data structure.

## 5. Micro-optimisations that are actually real

- Local variable lookup beats global beats attribute. In a hot loop:
  `append = result.append` then call `append(x)`.
- Comprehensions beat `for`+`append` (no method-call overhead per item).
- `str.join` beats `+=`. `f"{}"` beats `%` and `.format`.
- Avoid work in loop conditions; hoist invariants out.
- `try/except` is nearly free when nothing raises, and expensive when it does — prefer
  EAFP for the common case, LBYL when exceptions are the norm.
- `functools.partial` and `operator.itemgetter` beat lambdas in `key=` (C-level).

Everything above is worth 10–50%. Fixing an algorithm is worth 100×. Do that first.

## 6. Leaving Python

| Option | When |
|---|---|
| **numpy / polars / pyarrow** | array and dataframe work — vectorise, don't loop |
| **Cython / mypyc** | annotate existing Python, compile it |
| **PyO3 (Rust) / pybind11 (C++)** | a genuinely hot kernel |
| **numba** | numeric loops, JIT with a decorator |
| **subinterpreters / free-threading** | CPU parallelism inside one process (module 10) |

**3.13+**: an experimental JIT (`PYTHON_JIT=1`) and the free-threaded build. 3.11 was
already ~25% faster than 3.10 for free — *upgrading your interpreter is the cheapest
optimisation available*.

## 7. Benchmarking honestly

- Warm up first; discard the first run (imports, caches, branch prediction).
- Take the **minimum** of N runs for micro-benchmarks (noise only adds time), but the
  **distribution** for end-to-end work.
- Benchmark realistic data sizes — asymptotics don't show up at n=10.
- Change one thing at a time, and re-measure after every change.

## Exercises

`exercises_13.py`, then `pytest 13_performance`. Each one is a slow implementation you
must make fast **without changing the behaviour** — the tests check correctness first and
complexity second (by timing a large input against a strict budget).

There's also `bench_13.py`: run `python 13_performance/bench_13.py` to see before/after
numbers for your own implementations.

## Further reading

- [`cProfile`](https://docs.python.org/3/library/profile.html), [`tracemalloc`](https://docs.python.org/3/library/tracemalloc.html)
- [py-spy](https://github.com/benfred/py-spy), [memray](https://github.com/bloomberg/memray)
