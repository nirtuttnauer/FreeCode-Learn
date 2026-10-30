# 06 — Iterators, generators, `itertools`

Laziness is Python's answer to "the data doesn't fit in memory" and to "I want composable
pipelines without building intermediates".

## In plain English

Say you want to process a billion lines of a log file.

The obvious approach is to load them all into a list first. That's like baking a thousand
pizzas before anyone has ordered — you need somewhere to put them all, and you spent hours
before serving the first slice.

A **generator** makes one at a time, on demand. You ask for the next line, it gives you the
next line, and it doesn't do a single bit of work until you ask again. Memory use stays flat
whether the file has ten lines or ten billion, and you get your first result immediately.

The magic word is `yield`. A function with `yield` in it doesn't run when you call it —
it hands you a thing that will run *a bit at a time*, pausing at each `yield` and picking up
exactly where it left off when you ask for more.

**Watch out for:** generators are **one-shot**. Once you've walked through it, it's empty.
Loop over it twice and the second loop sees nothing at all — no error, just silence. This
catches everybody once.

## 1. Iterable vs iterator

- **Iterable**: has `__iter__` returning a fresh iterator. Reusable. (`list`, `dict`, `str`)
- **Iterator**: has `__next__` **and** `__iter__` returning `self`. One-shot, stateful.
  Exhausted iterators raise `StopIteration` forever.

```python
it = iter([1, 2, 3])
next(it)              # 1
list(it), list(it)    # [2, 3] then []  <- gone
```

This is the source of a classic bug: passing a generator to two functions and wondering
why the second sees nothing. If you need to reuse it, make a **class with `__iter__` that
returns a new generator each call**, or materialise it into a list.

`next(it, default)` avoids `StopIteration`.

## 2. Generator functions

Any `def` containing `yield` returns a generator when called; the body doesn't run until
you iterate.

```python
def read_records(path):
    with open(path) as fh:        # the `with` stays open across yields
        for line in fh:           # files are iterators of lines — never .readlines()
            yield parse(line)
```

State machine: **created → suspended at each yield → resumed → exhausted**. On exhaustion
`return value` sets `StopIteration.value` (what `yield from` picks up).

`yield from sub_iterable` delegates iteration *and* `send`/`throw` — that's the whole
mechanism behind old-style coroutines.

## 3. Generators as coroutines: `send`, `throw`, `close`

```python
def averager():
    total = count = 0
    average = None
    while True:
        value = yield average      # yield produces, then RECEIVES the sent value
        total += value
        count += 1
        average = total / count

avg = averager()
next(avg)          # "prime" it: run to the first yield
avg.send(10)       # 10.0
avg.close()        # raises GeneratorExit inside; wrap cleanup in try/finally
```

Priming is mandatory — `send` to a just-created generator is a `TypeError`.

## 4. Pipelines

```python
lines    = (l.rstrip("\n") for l in file)
records  = (parse(l) for l in lines if l)
filtered = (r for r in records if r.status == "ok")
total    = sum(r.amount for r in filtered)      # one pass, O(1) memory
```

Each stage adds no memory. Compare with the list-comprehension version, which materialises
every intermediate.

## 5. `itertools` — the ones that earn their keep

| Function | Does |
|---|---|
| `chain(a, b)` / `chain.from_iterable(lists)` | concatenate lazily |
| `islice(it, start, stop, step)` | slice an iterator (no negative indices) |
| `groupby(it, key)` | group **consecutive** runs — sort first, or you get surprises |
| `tee(it, n)` | n independent iterators (buffers in memory — don't tee a huge one) |
| `zip_longest(a, b, fillvalue=)` | ragged zip |
| `pairwise(it)` | `(a,b), (b,c), (c,d)` — 3.10+ |
| `batched(it, n)` | fixed-size chunks — **3.12+**, replaces hand-rolled versions |
| `accumulate(it, func)` | running totals |
| `count/cycle/repeat` | infinite sources — always bound with `islice`/`takewhile` |
| `takewhile/dropwhile/filterfalse/compress` | lazy filters |
| `product/permutations/combinations` | combinatorics without recursion |

Plus builtins: `zip(strict=True)` (3.10+ — catches length mismatches), `enumerate(start=)`,
`map`, `filter`, `any`/`all`, `sum`, `min`/`max(key=, default=)`, `sorted`, `reversed`.

## 6. Memory: the actual point

```python
sys.getsizeof([x*x for x in range(1_000_000)])   # ~8 MB
sys.getsizeof((x*x for x in range(1_000_000)))   # ~200 bytes
```

But: a generator is *slower per element* than a list comprehension when you need all the
elements anyway. Lazy for streams, eager for small collections you'll traverse twice.

## 7. Generator gotchas

- **One-shot.** `sum(g)` then `max(g)` → the second is 0/error.
- `len()` doesn't work. `sum(1 for _ in it)` consumes it.
- Exceptions inside a generator surface at the `next()` call site, not at creation.
- A `return` inside a generator ends iteration; the value goes to `StopIteration.value`.
- Don't `yield` inside a `try` that holds a lock unless you understand that the lock stays
  held while suspended.
- Late binding applies to generators too: `(f(x) for x in items)` reads `f` at iteration
  time, not creation time.

## Exercises

`exercises_06.py`, then `pytest 06_iterators_generators`.

## Further reading

- [`itertools`](https://docs.python.org/3/library/itertools.html) — read the recipes section
- [PEP 380 — `yield from`](https://peps.python.org/pep-0380/)
