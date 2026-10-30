"""Module 06 — runnable lesson. `python 06_iterators_generators/lesson_06.py`"""

from __future__ import annotations

import itertools
import sys
from collections.abc import Iterator

INTRO = """A list is a thousand pizzas baked before anyone ordered. A generator makes one slice each
time you ask. Same result, but constant memory and your first slice arrives immediately —
which is the difference between processing a billion-line file and crashing."""


def iterable_vs_iterator() -> None:
    print("\n== iterable vs iterator ==")
    data = [1, 2, 3]
    it = iter(data)
    print(f"  {iter(data) is not iter(data)=}  (a list gives a FRESH iterator each time)")
    print(f"  {iter(it) is it=}  (an iterator returns itself)")
    print(f"  next(it)={next(it)}, rest={list(it)}, again={list(it)}  <- exhausted")
    print(f"  next(it, 'default') = {next(it, 'default')}")

    class Countdown:
        """Reusable iterable: __iter__ returns a NEW generator every time."""

        def __init__(self, start: int) -> None:
            self.start = start

        def __iter__(self) -> Iterator[int]:
            n = self.start
            while n > 0:
                yield n
                n -= 1

    c = Countdown(3)
    print(f"  reusable: {list(c)} then {list(c)}")


def generator_mechanics() -> None:
    print("\n== generator state machine ==")

    def gen():
        print("    body starts (only on first next())")
        yield 1
        print("    resumed after first yield")
        yield 2
        print("    resumed after second yield")
        return "done"  # becomes StopIteration.value

    g = gen()
    print(f"  created, nothing ran yet: {g}")
    print(f"  next -> {next(g)}")
    print(f"  next -> {next(g)}")
    try:
        next(g)
    except StopIteration as stop:
        print(f"  StopIteration.value = {stop.value!r}")

    def outer():
        result = yield from inner()  # delegates, and captures the return value
        print(f"    inner returned {result!r}")
        yield "after"

    def inner():
        yield "a"
        yield "b"
        return "inner-result"

    print(f"  yield from: {list(outer())}")


def coroutine_generators() -> None:
    print("\n== send / throw / close ==")

    def averager():
        total = count = 0
        average = None
        try:
            while True:
                value = yield average  # produces `average`, receives the sent value
                total += value
                count += 1
                average = total / count
        finally:
            print("    averager cleaning up (GeneratorExit)")

    avg = averager()
    next(avg)  # prime: run to the first yield
    print(f"  send(10) -> {avg.send(10)}")
    print(f"  send(20) -> {avg.send(20)}")
    print(f"  send(30) -> {avg.send(30)}")
    avg.close()

    fresh = averager()
    try:
        fresh.send(1)
    except TypeError as exc:
        print(f"  sending to an unprimed generator: {exc}")


def pipelines_and_memory() -> None:
    print("\n== lazy pipeline, constant memory ==")
    raw = (f"user{n},{n * 10},{'ok' if n % 3 else 'error'}" for n in range(1, 1_000_001))
    fields = (line.split(",") for line in raw)
    parsed = ((name, int(amount)) for name, amount, status in fields if status == "ok")
    total = sum(amount for _, amount in parsed)
    print(f"  summed 1M rows lazily: {total:,}")

    listcomp = [x * x for x in range(100_000)]
    genexp = (x * x for x in range(100_000))
    print(f"  list of 100k: {sys.getsizeof(listcomp):>9,} bytes")
    print(f"  generator:    {sys.getsizeof(genexp):>9,} bytes")


def itertools_tour() -> None:
    print("\n== itertools ==")
    print(f"  chain:        {list(itertools.chain([1, 2], [3]))}")
    print(f"  islice:       {list(itertools.islice(itertools.count(10), 3))}")
    print(f"  pairwise:     {list(itertools.pairwise([1, 2, 3, 4]))}")
    print(f"  batched:      {list(itertools.batched(range(7), 3))}  (3.12+)")
    print(f"  accumulate:   {list(itertools.accumulate([1, 2, 3, 4]))}")
    print(f"  zip_longest:  {list(itertools.zip_longest([1, 2], 'ab c', fillvalue='-'))[:3]}")
    print(f"  takewhile:    {list(itertools.takewhile(lambda n: n < 3, [1, 2, 3, 1]))}")
    print(f"  dropwhile:    {list(itertools.dropwhile(lambda n: n < 3, [1, 2, 3, 1]))}")
    print(f"  combinations: {list(itertools.combinations('abc', 2))}")

    print("\n  groupby only groups CONSECUTIVE runs:")
    data = ["apple", "avocado", "banana", "apricot"]
    unsorted = {k: list(v) for k, v in itertools.groupby(data, key=lambda w: w[0])}
    sorted_first = {
        k: list(v) for k, v in itertools.groupby(sorted(data), key=lambda w: w[0])
    }
    print(f"    unsorted input: {unsorted}   <- 'a' appears twice, second overwrote first")
    print(f"    sorted first:   {sorted_first}")

    a, b = itertools.tee(iter([1, 2, 3]))
    print(f"  tee gives independent iterators: {list(a)} {list(b)}")


def gotchas() -> None:
    print("\n== gotchas ==")
    g = (n for n in range(5))
    print(f"  sum(g)={sum(g)} then max(g, default='EMPTY')={max(g, default='EMPTY')}")

    try:
        len(n for n in range(3))
    except TypeError as exc:
        print(f"  len(genexp): {exc}")

    def raises():
        yield 1
        raise ValueError("surfaces at the 2nd next(), not at creation")

    r = raises()  # no exception here
    print(f"  created fine, first item = {next(r)}")
    try:
        next(r)
    except ValueError as exc:
        print(f"  second next(): {exc}")

    print(f"  zip(strict=True) catches length bugs:")
    try:
        list(zip([1, 2, 3], [1, 2], strict=True))
    except ValueError as exc:
        print(f"    {exc}")


if __name__ == "__main__":
    print(INTRO)
    iterable_vs_iterator()
    generator_mechanics()
    coroutine_generators()
    pipelines_and_memory()
    itertools_tour()
    gotchas()
