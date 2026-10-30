# 02 — Data structures, comprehensions, `collections`

Choosing the right container is 80% of Python performance work you'll ever do. This module
is about knowing the menu cold.

## In plain English

Think about where you keep your stuff.

- A **list** is a numbered shelf. Brilliant at "give me item #5". Terrible at "do we own a
  hammer?" — you have to check every single shelf, one by one.
- A **set** or **dict** is the index at the back of a book. It answers "do we own a hammer?"
  instantly, no matter how much stuff you have, because it computes *where the answer would
  be* instead of searching.

That's the whole module, really. Picking the right container is the single biggest
performance decision most programs ever make, and it takes about five seconds to get right
if you know the difference.

There's a real number attached: searching a list of a million items takes a million steps.
Searching a set of a million items takes about *one*. In the lesson you'll watch that gap
open up live.

**Watch out for:** writing `if thing in my_big_list` inside a loop. That's the classic
accidentally-slow program, and the fix is one line.

## 1. The complexity table (memorise this)

| Operation | `list` | `deque` | `dict` / `set` |
|---|---|---|---|
| index / key lookup | O(1) | O(n) | O(1) avg |
| append / add | O(1) amortised | O(1) | O(1) avg |
| insert / pop at front | **O(n)** | **O(1)** | — |
| `x in c` | **O(n)** | O(n) | **O(1) avg** |
| delete middle | O(n) | O(n) | O(1) avg |

The single most common performance bug in real code: `if x in big_list` inside a loop.
Convert to a `set` once and it goes from O(n·m) to O(n).

`dict` preserves insertion order (guaranteed since 3.7). `set` does not.

## 2. Tuples aren't "immutable lists"

Idiomatically, a `tuple` is a **record** (heterogeneous, position means something) and a
`list` is a **sequence** (homogeneous, order means sequence). A tuple can be a dict key —
if everything inside it is hashable.

`NamedTuple` gives you a record with names and still-tuple behaviour:

```python
from typing import NamedTuple

class Point(NamedTuple):
    x: float
    y: float = 0.0

p = Point(1, 2)
p.x, p[0], tuple(p), p._replace(x=9), p._asdict()
```

Use `NamedTuple` for lightweight immutable value objects; `@dataclass` (module 04) when you
want mutability, methods, or `__post_init__` validation.

## 3. Hashability

An object can be a `dict` key or `set` member iff it's hashable: `__hash__` is not `None`
and `__eq__` is consistent with it. Builtin immutables are hashable; `list`, `dict`, `set`
are not. `frozenset` is. If you define `__eq__` on a class, Python sets `__hash__ = None`
unless you define it too (module 04).

## 4. Comprehensions

```python
[f(x) for x in it if cond(x)]                 # list
{k: v for k, v in pairs}                      # dict
{f(x) for x in it}                            # set
(f(x) for x in it)                            # GENERATOR, not a tuple
[y for x in matrix for y in x]                # nested: read left-to-right as nested loops
[y for x in it if p(x) if q(x)]               # multiple filters
[a if cond else b for x in it]                # ternary goes in the VALUE slot
```

Rules of thumb:
- Two loops + one condition is the readability ceiling. Past that, write a `for` loop or a
  generator function.
- Comprehensions have their own scope — the loop variable does not leak (unlike `for`).
- Use a generator expression when feeding a consumer: `sum(x*x for x in it)` — no
  intermediate list. `any()`/`all()` short-circuit over them.

## 5. `collections` — the ones you should reach for

| Type | Use it for |
|---|---|
| `Counter` | frequency counts; `.most_common(n)`, supports `+ - & \|` |
| `defaultdict(list)` | grouping without `setdefault` noise |
| `deque(maxlen=N)` | FIFO queues, sliding windows, ring buffers |
| `ChainMap` | layered config lookup without merging |
| `namedtuple` | legacy of `NamedTuple`; still fine |

```python
Counter("mississippi").most_common(2)   # [('i', 4), ('s', 4)]
Counter(a) - Counter(b)                 # multiset difference, drops non-positive
```

`dict` since 3.9 supports `|` and `|=` for merging. `dict.get(k, default)`,
`dict.setdefault(k, default)`, `dict.pop(k, default)` — know which one mutates
(`setdefault` and `pop` do).

## 6. Sorting

```python
sorted(items, key=lambda r: (r.dept, -r.salary))    # multi-key, mixed direction
sorted(items, key=operator.attrgetter("dept", "name"))
sorted(words, key=str.casefold)
max(items, key=len)
heapq.nlargest(3, items, key=score)                  # better than sort when k << n
```

Python's sort is **stable** — so you can sort by secondary key first, then primary.
There is no `cmp`; use `functools.cmp_to_key` only when you're porting old code.

`bisect` gives you O(log n) insertion points into a sorted list — `bisect.insort`,
and `bisect_left(scores, target)` for range queries.

## 7. Set algebra

```python
a | b   # union            a.union(b)
a & b   # intersection     a.intersection(b)
a - b   # difference
a ^ b   # symmetric difference
a <= b  # subset           a < b proper subset
```

Operator forms require both sides to be sets; method forms accept any iterable.

## Exercises

`exercises_02.py`, then `pytest 02_data_structures`.

## Further reading

- [`collections` docs](https://docs.python.org/3/library/collections.html)
- [TimeComplexity wiki](https://wiki.python.org/moin/TimeComplexity)
