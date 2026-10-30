"""Module 02 — runnable lesson. `python 02_data_structures/lesson_02.py`"""

from __future__ import annotations

import bisect
import heapq
import operator
import time
from collections import ChainMap, Counter, defaultdict, deque
from typing import NamedTuple

INTRO = """A list is a numbered shelf: great at "give me #5", terrible at "do we have one?".
A set is the index at the back of a book: instant "do we have one?", however big it gets.
The first demo measures exactly how big that difference is."""


def why_sets_matter() -> None:
    print("\n== membership: list vs set ==")
    haystack_list = list(range(50_000))
    haystack_set = set(haystack_list)
    needles = range(0, 50_000, 500)

    t0 = time.perf_counter()
    sum(1 for n in needles if n in haystack_list)
    list_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    sum(1 for n in needles if n in haystack_set)
    set_time = time.perf_counter() - t0

    print(f"  list scan: {list_time * 1000:8.2f} ms")
    print(f"  set  hash: {set_time * 1000:8.2f} ms   ({list_time / set_time:.0f}x faster)")


def records_vs_sequences() -> None:
    print("\n== tuple as record, NamedTuple as better record ==")

    class Point(NamedTuple):
        x: float
        y: float = 0.0

    p = Point(3, 4)
    print(f"  {p=}  {p.x=}  {p[0]=}  {len(p)=}")
    print(f"  immutable update: {p._replace(y=99)=}")
    print(f"  {p._asdict()=}")
    print(f"  usable as a dict key because it's hashable: {{p: 'origin-ish'}}")

    # Tuples of hashables are hashable; lists never are.
    try:
        {[1, 2]: "nope"}
    except TypeError as exc:
        print(f"  list as key -> TypeError: {exc}")


def comprehensions() -> None:
    print("\n== comprehensions ==")
    matrix = [[1, 2, 3], [4, 5, 6]]
    print(f"  flatten:      {[y for row in matrix for y in row]}")
    print(f"  transpose:    {[list(col) for col in zip(*matrix, strict=True)]}")
    print(f"  dict comp:    { {w: len(w) for w in ['a', 'bb', 'ccc']} }")
    print(f"  set comp:     { {w[0] for w in ['apple', 'avocado', 'banana']} }")
    print(f"  ternary slot: {['even' if n % 2 == 0 else 'odd' for n in range(4)]}")
    print(f"  two filters:  {[n for n in range(30) if n % 3 == 0 if n % 5 == 0]}")

    # A genexp is lazy: nothing is computed until consumed.
    squares = (n * n for n in range(10**9))
    print(f"  genexp object: {squares}")
    print(f"  any() short-circuits: {any(n > 100 for n in range(10**9))}")

    # Comprehension scope does not leak.
    n = "outer"
    _ = [n for n in range(3)]
    print(f"  after comprehension, n is still {n!r}")


def collections_tour() -> None:
    print("\n== collections ==")
    c = Counter("mississippi")
    print(f"  {c.most_common(2)=}")
    print(f"  multiset math: {Counter('aab') - Counter('ab')=}")

    grouped: defaultdict[str, list[str]] = defaultdict(list)
    for word in ["apple", "avocado", "banana", "blueberry"]:
        grouped[word[0]].append(word)
    print(f"  defaultdict grouping: {dict(grouped)}")

    window: deque[int] = deque(maxlen=3)
    for n in range(6):
        window.append(n)
    print(f"  deque(maxlen=3) after 0..5: {list(window)}")
    print("  deque.appendleft/popleft are O(1); list.insert(0, x) is O(n)")

    defaults = {"host": "localhost", "port": 8080, "debug": False}
    env = {"port": 9000}
    cli = {"debug": True}
    config = ChainMap(cli, env, defaults)  # first mapping wins
    print(f"  ChainMap lookup: host={config['host']} port={config['port']} debug={config['debug']}")

    print(f"  dict merge with |: { {'a': 1} | {'b': 2} }")


def sorting() -> None:
    print("\n== sorting ==")
    people = [
        {"name": "ada", "dept": "eng", "salary": 200},
        {"name": "bob", "dept": "eng", "salary": 150},
        {"name": "cy", "dept": "ops", "salary": 180},
    ]
    by_dept_then_pay = sorted(people, key=lambda r: (r["dept"], -r["salary"]))
    print(f"  multi-key: {[p['name'] for p in by_dept_then_pay]}")

    print(f"  attrgetter/itemgetter: {[p['name'] for p in sorted(people, key=operator.itemgetter('name'))]}")
    print(f"  top-2 without a full sort: {heapq.nlargest(2, people, key=operator.itemgetter('salary'))[0]['name']}")

    scores = [10, 20, 30, 40, 50]
    print(f"  bisect_left(scores, 35) = {bisect.bisect_left(scores, 35)} (insertion point)")
    print("  stable sort => sort by secondary key first, then primary")


def set_algebra() -> None:
    print("\n== set algebra ==")
    a, b = {1, 2, 3, 4}, {3, 4, 5}
    print(f"  {a | b=}\n  {a & b=}\n  {a - b=}\n  {a ^ b=}\n  {a >= {1, 2}=}")
    print(f"  method form takes any iterable: {a.union([9, 10])=}")


if __name__ == "__main__":
    print(INTRO)
    why_sets_matter()
    records_vs_sequences()
    comprehensions()
    collections_tour()
    sorting()
    set_algebra()
