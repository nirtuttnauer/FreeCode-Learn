"""Module 01 — runnable lesson. `python 01_core_refresher/lesson_01.py`

Read top to bottom; every section prints something you should be able to predict
*before* you run it. Cover the output, guess, then check.
"""

from __future__ import annotations

import copy
import math
from decimal import Decimal

INTRO = """A variable in Python is a sticky LABEL, not a box. `b = a` sticks a second label on
the same thing — it does not copy it. Watch that happen below, then see how slicing,
truthiness, text and number formatting really behave."""


def names_and_objects() -> None:
    print("\n== names bind, they don't copy ==")
    a = [1, 2, 3]
    b = a
    b.append(4)
    print(f"{a=} {b=} {a is b=}")

    shallow = copy.copy([[1], [2]])
    nested = [[1], [2]]
    shallow = nested[:]
    nested[0].append("mutated")
    print(f"shallow copy shares inner lists: {shallow=}")

    deep = copy.deepcopy(nested)
    nested[0].append("again")
    print(f"deep copy is independent:        {deep=}")

    # Identity is not equality.
    x, y = [1, 2], [1, 2]
    print(f"{x == y=}  {x is y=}")


def truthiness() -> None:
    print("\n== truthiness ==")
    for value in [0, 0.0, "", [], {}, set(), None, "0", [0], Decimal(0)]:
        print(f"  bool({value!r:>10}) = {bool(value)}")

    class Empty:
        def __len__(self) -> int:
            return 0

    class Never:
        def __bool__(self) -> bool:
            return False

    print(f"  __len__-based falsiness: {bool(Empty())}")
    print(f"  __bool__-based falsiness: {bool(Never())}")


def slicing() -> None:
    print("\n== slicing ==")
    s = list(range(10))
    print(f"  {s[2:5]=}  {s[::2]=}  {s[::-1]=}  {s[-3:]=}")
    print(f"  out of range never raises: {s[100:200]=}")

    spliced = s[:]
    spliced[1:4] = ["a"]  # length changes
    print(f"  splice: {spliced}")

    first, *middle, last = s
    print(f"  unpack: {first=} {last=} {len(middle)=}")

    # Slices are objects; you can name them.
    payload = slice(2, 5)
    print(f"  named slice: {s[payload]=}")


def strings_and_bytes() -> None:
    print("\n== str vs bytes ==")
    text = "héllo"
    raw = text.encode("utf-8")
    print(f"  {text=} {len(text)=}")
    print(f"  {raw=}   {len(raw)=}")
    print(f"  round trip ok: {raw.decode('utf-8') == text}")

    print("\n== string methods worth knowing ==")
    print(f"  {'  a  b   c '.split()=}")            # splits on runs of whitespace
    print(f"  {'a,b,,c'.split(',')=}")               # keeps empties
    print(f"  {'key=value=extra'.partition('=')=}")
    print(f"  {'prefix_body'.removeprefix('prefix_')=}")
    print(f"  {'file.tar.gz'.endswith(('.gz', '.zip'))=}")
    print(f"  {'STRASSE'.casefold() == 'strasse'=}")


def fstrings() -> None:
    print("\n== f-string mini-language ==")
    v = 1234.5678
    print(f"  {v:,.2f}     thousands separator")
    print(f"  {v:>12,.2f}  right aligned in 12")
    print(f"  {v:<12,.2f}| left aligned")
    print(f"  {v:^12,.2f}| centered")
    print(f"  {v:*>12,.2f}  custom fill")
    print(f"  {v:+.1f}      forced sign")
    print(f"  {v:.2e}      scientific")
    print(f"  {255:#06x}     hex, zero padded, with 0x")
    print(f"  {0.756:.1%}     percentage")
    width, prec = 10, 3
    print(f"  {v:{width}.{prec}f}  nested spec")
    print(f"  {v = }        the debug form")


def numbers() -> None:
    print("\n== numeric surprises ==")
    print(f"  {-7 // 2=}   (floors toward -inf)")
    print(f"  {-7 % 2=}    (sign follows the divisor)")
    print(f"  {divmod(-7, 2)=}")
    print(f"  {0.1 + 0.2 == 0.3=}  ->  use math.isclose: {math.isclose(0.1 + 0.2, 0.3)}")
    print(f"  {Decimal('0.1') + Decimal('0.2') == Decimal('0.3')=}")
    print(f"  {round(0.5)=} {round(1.5)=} {round(2.5)=}  (banker's rounding)")
    print(f"  big ints are exact: {2**70=}")


def walrus_and_conditionals() -> None:
    print("\n== walrus ==")
    data = list(range(15))
    if (n := len(data)) > 10:
        print(f"  {n} items is a lot")
    # Common real use: loop while a call returns something.
    chunks = iter([b"ab", b"cd", b""])
    while chunk := next(chunks):
        print(f"  got {chunk!r}")


def mutators_return_none() -> None:
    print("\n== mutators return None ==")
    lst = [3, 1, 2]
    print(f"  {lst.sort()=}  <- None! the list itself is now {lst}")
    print(f"  {sorted([3, 1, 2])=}  <- the non-mutating twin")
    print(f"  {list(reversed([1, 2, 3]))=}")


if __name__ == "__main__":
    print(INTRO)
    names_and_objects()
    truthiness()
    slicing()
    strings_and_bytes()
    fstrings()
    numbers()
    walrus_and_conditionals()
    mutators_return_none()
