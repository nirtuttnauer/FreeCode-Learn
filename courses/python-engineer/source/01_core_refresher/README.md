# 01 — Core refresher: the object model, sequences, strings

You know what a variable is. What you may have half-forgotten is that **Python has no
variables in the C sense** — it has *names bound to objects*. Almost every "weird Python
behaviour" you'll hit for the rest of this course comes from that one fact.

## In plain English

Imagine a variable is not a box you put a value into, but a **sticky label you slap onto a
thing**. `a = [1, 2, 3]` doesn't create a box called `a` — it creates a list somewhere in
memory and sticks the label `a` on it. Write `b = a` and you haven't copied anything; you've
stuck a *second* label on the *same* list. Now if you change the list through `b`, someone
looking at `a` sees the change too, because there was only ever one list.

Almost every "wait, why did Python do that?!" moment for the rest of this course traces back
to that one idea. Hold onto it.

The rest of this module is the everyday toolkit: how to slice pieces out of things, how
Python decides whether something counts as "yes" or "no" in an `if`, how text really works
(and why emoji break naive code), and how to format numbers nicely.

**Watch out for:** `is` vs `==`. `==` asks "do these two things look the same?"; `is` asks
"are these literally the same object?" Two identical twins are `==` but not `is`.

## 1. Names, objects, and mutation

```python
a = [1, 2, 3]
b = a          # NOT a copy — a second name for the same object
b.append(4)
a              # [1, 2, 3, 4]
```

- `=` **binds a name**. It never copies and never mutates.
- `x.attr = v`, `x[i] = v`, `x.append(v)` **mutate the object** every name sees.
- `is` compares identity (`id()`), `==` compares value (`__eq__`).

Interning traps: `256 is 256` → `True`, `1000 is 1000` → depends on compilation unit.
**Never use `is` for numbers or strings.** Use it only for `None`, `True`, `False`, and
sentinel objects.

Copying:

```python
import copy
shallow = original[:]            # or list(original), copy.copy(original)
deep    = copy.deepcopy(original)
```

## 2. Everything is an object, including functions and classes

`type(x)` is itself an object of type `type`. Functions have `__name__`, `__doc__`,
`__defaults__`, `__code__`. This is the foundation for modules 03 and 12.

## 3. Truthiness

`if x:` calls `bool(x)`, which uses `__bool__`, falling back to `__len__`, falling back to
`True`. Falsy builtins: `False`, `None`, `0`, `0.0`, `Decimal(0)`, `""`, `[]`, `{}`, `()`,
`set()`, `range(0)`.

The classic bug:

```python
def f(items=None):
    if not items:          # WRONG if [] and None must be distinguished
        items = default()
    if items is None:      # right
        items = default()
```

## 4. Sequences and slicing

`seq[start:stop:step]` — `stop` is exclusive, all parts optional, negative indices count
from the end, and **out-of-range slices don't raise** (`[1,2,3][10:20] == []`).

| Idiom | Meaning |
|---|---|
| `s[::-1]` | reversed copy |
| `s[::2]` | every second element |
| `s[:]` | shallow copy (lists) |
| `del lst[1:3]` | delete a range in place |
| `lst[1:3] = [9]` | splice — length can change |

Unpacking (works on any iterable):

```python
first, *rest = [1, 2, 3, 4]        # 1, [2, 3, 4]
a, (b, c) = 1, (2, 3)              # nested
first, *_, last = data             # ignore the middle
```

## 5. Strings are Unicode; bytes are bytes

`str` is a sequence of code points. `bytes` is a sequence of 0–255 ints. Converting always
requires an explicit codec:

```python
b = "héllo".encode("utf-8")     # str -> bytes
s = b.decode("utf-8")           # bytes -> str
```

Never let them meet implicitly. `len("héllo") == 5` but `len(b) == 6`.

Useful methods you should not re-implement: `.strip/.lstrip/.rstrip`, `.split/.rsplit`
(no-arg `.split()` splits on *runs* of whitespace), `.partition`, `.join`, `.removeprefix`,
`.removesuffix`, `.startswith/.endswith` (accept tuples!), `.casefold` (better than `.lower`
for comparisons), `.translate`, `.zfill`.

`"".join(parts)` is O(n); `s += part` in a loop is O(n²)-ish. See module 13.

## 6. The f-string mini-language

```python
f"{value!r:>10.3f}"
#  │      │  │ │ └ precision
#  │      │  │ └── type
#  │      │  └──── width
#  │      └─────── align (< ^ > =) and optional fill char
#  └────────────── conversion: !r repr, !s str, !a ascii
```

Worth memorising:

| Spec | Result for `1234.5678` |
|---|---|
| `{v:,.2f}` | `1,234.57` |
| `{v:_.2f}` | `1_234.57` |
| `{v:>12,.2f}` | `␣␣␣␣1,234.57` |
| `{v:.2e}` | `1.23e+03` |
| `{v:+.1f}` | `+1234.6` |
| `{255:#06x}` | `0x00ff` |
| `{0.756:.1%}` | `75.6%` |
| `{name=}` | `name=<repr>` — debugging gold (3.8+) |

Nested spec: `f"{value:{width}.{prec}f}"`.

## 7. Numbers

- `/` is true division, `//` is floor division (**floors toward −∞**: `-7 // 2 == -4`).
- `%` follows the sign of the divisor: `-7 % 2 == 1`.
- `divmod(a, b)` gives both.
- `float` is IEEE-754: `0.1 + 0.2 != 0.3`. Use `math.isclose` for comparisons, `Decimal`
  for money, `Fraction` for exact rationals.
- `int` is arbitrary precision. `10**100` is fine.
- `math.isqrt`, `round()` uses **banker's rounding**: `round(0.5) == 0`, `round(1.5) == 2`.

## 8. Walrus and conditional expressions

```python
if (n := len(data)) > 10:      # assign inside an expression
    print(f"{n} items")

status = "ok" if ok else "fail"
```

## Gotcha checklist

- [ ] Mutable default arguments (module 03 — but know it now)
- [ ] `is` vs `==`
- [ ] `not items` vs `items is None`
- [ ] Late-binding closures in loops (module 03)
- [ ] `list.sort()` returns `None`; `sorted()` returns a new list. Same for
      `reverse()`/`reversed()`, `.append()` etc. — **mutators return None**.

## Exercises

Implement everything in `exercises_01.py`, then `pytest 01_core_refresher`.

## Further reading

- [Python Data Model](https://docs.python.org/3/reference/datamodel.html) — the single most
  valuable document in the docs; you'll return to it in modules 04, 06 and 12.
- [Format Specification Mini-Language](https://docs.python.org/3/library/string.html#formatspec)
