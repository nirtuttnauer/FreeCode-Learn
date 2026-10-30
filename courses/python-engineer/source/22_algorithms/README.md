# 22 — Data structures and algorithms, in Python

You did this in your degree. This module is about the *Python* layer on top: which
stdlib tool already implements the structure you were about to hand-roll, and how the
classic algorithms look when written idiomatically.

## In plain English

Two things here: knowing which tools already exist, and knowing how to talk about cost.

**The tools.** Python ships with a priority queue (`heapq`), a double-ended queue
(`deque`), binary search (`bisect`), and a topological sort (`graphlib`). People reimplement
these constantly, usually worse. Writing them yourself once, to understand them, is a great
exercise — shipping your own version is usually a mistake.

**The cost language.** "Big-O" sounds academic but the idea is simple: *when the input gets
bigger, how much worse does this get?*

- O(1) — same cost no matter what. Looking up a word in a dictionary.
- O(log n) — barely grows. Guessing a number 1–1,000,000 by halving takes 20 guesses.
- O(n) — grows in step. Reading every page of a book.
- O(n log n) — the practical limit for sorting.
- O(n²) — grows *brutally*. Everyone shaking hands with everyone else.

The whole point is what happens as things scale. An O(n²) algorithm on 100 items is
instant. The same code on 100,000 items does ten billion operations and looks like it has
frozen. Same code, no bug — just the wrong shape.

**Watch out for:** Python's recursion limit (~1000 calls deep) and the lack of tail-call
optimisation. A recursion that's elegant in a textbook can simply crash here; the lesson
shows how to convert it to a loop.

## 1. Use the batteries first

| You were about to write | Use instead |
|---|---|
| A dynamic array | `list` |
| A hash map / set | `dict` / `set` (open addressing, C-speed) |
| A doubly-linked list, queue, ring buffer | `collections.deque` |
| A binary heap / priority queue | `heapq` |
| A sorted-array insert or binary search | `bisect` |
| An LRU cache | `functools.lru_cache`, or `OrderedDict.move_to_end` |
| A counter / multiset | `collections.Counter` |
| A grouping dict | `collections.defaultdict` |
| A merge of sorted streams | `heapq.merge` |
| A topological sort | `graphlib.TopologicalSorter` (3.9+) |

Writing these yourself is a *learning* exercise (and this module makes you do a few). In
production code, the stdlib version is C, tested by millions of users, and shorter.

## 2. Complexity, with Python's constant factors

Big-O is necessary and not sufficient — an O(n log n) numpy sort beats an O(n) pure-Python
loop until n gets big, because the constant factor is ~50×.

| Structure | Access | Search | Insert | Delete |
|---|---|---|---|---|
| `list` | O(1) | O(n) | O(1) end, O(n) middle | O(n) |
| `deque` | O(n) | O(n) | **O(1) both ends** | O(1) both ends |
| `dict`/`set` | — | O(1) avg | O(1) avg | O(1) avg |
| `heapq` | O(1) min | O(n) | O(log n) | O(log n) pop-min |
| sorted list + `bisect` | O(1) | O(log n) | O(n) (the shift) | O(n) |

Amortised analysis matters: `list.append` is O(1) *amortised* because the array doubles.

## 3. Recursion in Python

The recursion limit is ~1000 frames and there's **no tail-call optimisation**. So:

- Convert deep recursion to iteration with an explicit stack.
- Memoise with `functools.cache` — it turns exponential recursions into linear ones.
- `sys.setrecursionlimit` is a way to turn a clean `RecursionError` into a segfault; it's
  not a fix.
- Divide and conquer on a balanced structure (depth ~log n) is fine recursively.

## 4. Sorting

`sorted()`/`list.sort()` are **Timsort**: O(n log n) worst case, O(n) on nearly-sorted
input, and **stable**. You will not beat it in Python.

What you actually need to know:
- `key=` is computed once per element (a Schwartzian transform, for free).
- Stability lets you sort by secondary key first, then primary.
- `heapq.nlargest(k, it)` is O(n log k) — better than sorting for small k.
- `bisect.insort` keeps a list sorted at O(n) per insert (the memmove is cheap; the
  algorithmic cost is real).

Know *why* quicksort/mergesort/heapsort differ (in-place vs stable vs worst case) for the
interview; reach for `sorted` in the job.

## 5. Graphs

Represent as `dict[node, list[node]]` — an adjacency map. Then:

- **BFS** with a `deque` → shortest path in an unweighted graph.
- **DFS** with an explicit stack (or recursion when depth is bounded) → cycles,
  components, topological order.
- **Dijkstra** with `heapq` → shortest path with non-negative weights. Use the lazy
  variant: push `(distance, node)`, and skip a popped node you've already settled.
- **Topological sort** → `graphlib.TopologicalSorter`, or Kahn's algorithm with in-degrees.
  A cycle means "no valid order" — detect it, don't loop forever.
- A* is Dijkstra plus a heuristic; correct only when the heuristic never overestimates.

## 6. Dynamic programming

Two forms of the same thing:
- **Top-down**: plain recursion + `@functools.cache`. Write the recurrence, add one
  decorator, done.
- **Bottom-up**: fill a table. More code, no recursion limit, and you can often drop to
  O(width) memory by keeping only the last row.

The recurrence is the hard part; the code is mechanical.

## 7. Interview-shaped patterns worth having ready

Two pointers, sliding window (module 02's `sliding_max`), fast/slow pointers (cycle
detection), prefix sums, monotonic stack/deque, binary search **on the answer**, union-find,
backtracking with pruning, top-k with a heap.

## 8. Measure before you optimise

An O(n²) algorithm on n=100 is 10,000 operations — instant. Correct and simple beats
clever until the profiler (module 13) says otherwise.

## Exercises

`exercises_22.py`, then `pytest 22_algorithms`. Several are deliberately "reimplement what
the stdlib gives you" — the tests check both correctness *and* complexity, so a working
but quadratic answer fails.

## Further reading

- [`heapq`](https://docs.python.org/3/library/heapq.html), [`bisect`](https://docs.python.org/3/library/bisect.html), [`graphlib`](https://docs.python.org/3/library/graphlib.html)
- *Introduction to Algorithms* (CLRS) for the theory; LeetCode/Advent of Code for the reps
