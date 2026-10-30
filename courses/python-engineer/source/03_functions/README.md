# 03 — Functions, closures, `functools`

Functions in Python are objects with a rich calling protocol. Half of "advanced Python"
is just using that protocol deliberately.

## In plain English

A function is a recipe. You hand it ingredients, it hands you back a dish.

But in Python, functions are also *things you can carry around* — you can put one in a list,
pass it to another function, or return one. That unlocks two ideas that look like magic
until they click:

- A **closure** is a recipe that secretly remembers an ingredient you gave it earlier. Make
  a "multiply by 3" function once, and it remembers the 3 forever.
- A **decorator** is gift-wrapping. You hand over a function, and you get back the same
  function wrapped in extra behaviour — timing it, logging it, retrying it — without editing
  the original at all.

**Watch out for:** the famous mutable-default trap. If you write `def f(items=[])`, that
list is created **once**, when Python first reads the function — not fresh on each call. So
it quietly accumulates junk between calls, and people lose entire afternoons to it. The
lesson shows it happening.

## 1. The full parameter grammar

```python
def f(pos_only, /, standard, *args, kw_only, **kwargs): ...
#     ─────────  ─  ────────  ─────  ───────  ────────
#         │      │      │       │       │        └ collects extra keywords (dict)
#         │      │      │       │       └────────── MUST be passed by name
#         │      │      │       └────────────────── collects extra positionals (tuple)
#         │      │      └────────────────────────── positional or keyword
#         │      └───────────────────────────────── everything left of / is positional-only
#         └──────────────────────────────────────── ...like this one
```

- A bare `*` starts keyword-only params without collecting: `def f(a, *, b)`.
- Positional-only (`/`, 3.8+) lets you rename params later without breaking callers, and
  lets a param be named `id`/`type` without clashing with a keyword.
- **Keyword-only for booleans and options.** `resize(img, True)` is unreadable;
  `resize(img, *, upscale=True)` forces `resize(img, upscale=True)`.

At the call site, `*` and `**` *unpack*:

```python
f(*args, **kwargs)
f(*[1, 2], **{"kw_only": 3})
```

## 2. Default arguments are evaluated **once**, at definition time

```python
def bad(item, target=[]):      # the SAME list every call
    target.append(item)
    return target

bad(1); bad(2)                 # [1, 2]  <- surprise
```

The fix:

```python
def good(item, target=None):
    if target is None:
        target = []
```

Same trap with `datetime.now()`, `{}`, or any object built in the signature. Use `None` +
a sentinel. When `None` is a legal value, make your own sentinel:

```python
_MISSING = object()
def get(key, default=_MISSING): ...
```

## 3. Closures and late binding

A closure captures the **variable**, not its value:

```python
fns = [lambda: i for i in range(3)]
[f() for f in fns]            # [2, 2, 2]  — all see the final i

fns = [lambda i=i: i for i in range(3)]      # bind now via default
fns = [functools.partial(lambda i: i, i) for i in range(3)]   # or partial
```

`nonlocal` rebinds an enclosing-scope name; `global` rebinds a module-level one. Reading
doesn't need either — only assignment does. The LEGB lookup order is
**L**ocal → **E**nclosing → **G**lobal → **B**uiltins.

Inspect a closure: `f.__closure__[0].cell_contents`, `f.__code__.co_freevars`.

## 4. `functools`

| Tool | What it buys you |
|---|---|
| `@cache` / `@lru_cache(maxsize=n)` | memoisation; args must be hashable; `.cache_clear()`, `.cache_info()` |
| `@cached_property` | compute once per *instance*, store in `__dict__` (needs no `__slots__` conflict) |
| `partial(f, a, kw=1)` | pre-bind arguments; picklable, unlike a lambda |
| `@wraps(f)` | copy `__name__`/`__doc__`/`__wrapped__` onto a wrapper — always use in decorators |
| `reduce(f, it, init)` | left fold; usually a plain loop is clearer |
| `@singledispatch` | type-based dispatch (module 14) |
| `@total_ordering` | fill in the other comparisons from `__eq__` + `__lt__` |
| `cmp_to_key` | port an old comparator to a sort key |

`@cache` on a method keeps instances alive forever (the cache holds `self`). Use
`@cached_property`, or cache a module-level function that takes plain values.

## 5. Decorators

```python
import functools

def logged(func):
    @functools.wraps(func)                 # without this, func.__name__ becomes "wrapper"
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        print(f"{func.__name__} -> {result!r}")
        return result
    return wrapper
```

A decorator *with arguments* is a function returning a decorator — three levels:

```python
def retry(times):                 # 1. takes the config
    def decorator(func):          # 2. takes the function
        @functools.wraps(func)
        def wrapper(*a, **kw):    # 3. takes the call
            ...
        return wrapper
    return decorator
```

`@decorator` is exactly `f = decorator(f)`. Stacking applies **bottom-up**:

```python
@a
@b
def f(): ...        # f = a(b(f))
```

Module 12 goes deeper: class decorators, decorators that preserve signatures for type
checkers (`ParamSpec`), and `contextlib.ContextDecorator`.

## 6. Introspection

```python
import inspect
inspect.signature(f)                 # rich, respects __wrapped__
inspect.signature(f).bind(1, b=2).arguments
f.__defaults__, f.__kwdefaults__, f.__annotations__
```

## 7. Lambdas — when they're fine

Only as a throwaway expression passed to another function (`key=`, `default_factory=`).
If it needs a name, it needs `def`. Ruff/PEP 8 will tell you the same.

## Exercises

`exercises_03.py`, then `pytest 03_functions`.

## Further reading

- [`functools`](https://docs.python.org/3/library/functools.html)
- [Execution model / name binding](https://docs.python.org/3/reference/executionmodel.html)
