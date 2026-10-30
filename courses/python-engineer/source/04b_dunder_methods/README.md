# 04b — Dunder methods: the complete tour

Module 04 used dunders to build objects. This module treats them as a **subject**: what
exists, when the interpreter calls it, and the ones people get wrong.

The rule underneath everything: **implicit dunder lookups go through the TYPE, not the
instance.** `len(x)` is `type(x).__len__(x)`. Setting `x.__len__ = f` on an instance does
nothing. That's also why `__getattr__` can't intercept `len()`.

---

## In plain English

Here's the trick that makes Python feel magic: **Python asks your object questions using
secret method names.**

When you write `len(x)`, Python doesn't have some special knowledge about `x`. It literally
turns around and asks: "hey, do you have a `__len__`?" When you write `a + b`, it asks `a`:
"do you have an `__add__`?" When you write `for thing in x`, it asks for `__iter__`.

So the entire language is a set of questions, and if your object knows how to answer them, it
gets to behave exactly like a built-in type. Module 04 used a few of these. This module is
the full list of questions Python can ask, and what happens if you answer them.

Once this clicks, libraries stop being mysterious. A pandas DataFrame isn't special-cased in
Python — it just answers a *lot* of these questions.

**Watch out for:** `__getattr__` (which runs when someone asks for an attribute you don't
have). It's incredibly useful and it's a trapdoor: get it slightly wrong and your program
disappears into infinite recursion. The lesson triggers that bug on purpose so you can see
exactly what it looks like.

## 1. Construction and destruction

| Dunder | Called by | Notes |
|---|---|---|
| `__new__(cls, ...)` | instance creation | static method; returns the instance. Override for immutables (`int`, `str`, `tuple` subclasses) and singletons |
| `__init__(self, ...)` | after `__new__` | must return `None` |
| `__init_subclass__(cls)` | subclass definition | implicit classmethod — plugin registries (module 12) |
| `__set_name__(self, owner, name)` | class body assignment | how descriptors learn their attribute name (module 12) |
| `__del__` | GC, eventually | **timing not guaranteed**; use `weakref.finalize` instead |

## 2. Representation

| Dunder | Called by |
|---|---|
| `__repr__` | `repr()`, REPL, debugger, containers' repr, `f"{x!r}"` |
| `__str__` | `str()`, `print()`, `f"{x}"` — falls back to `__repr__` |
| `__format__(self, spec)` | `format()`, `f"{x:spec}"` |
| `__bytes__` | `bytes(x)` |

Always write `__repr__`. `__str__` only when the friendly form differs.

```python
def __format__(self, spec: str) -> str:
    if not spec:
        return str(self)
    return format(self.value, spec)      # delegate the spec to the wrapped value
```

## 3. Comparison, hashing, truth

`__eq__ __ne__ __lt__ __le__ __gt__ __ge__ __hash__ __bool__`

- Return `NotImplemented` (not `False`) for unsupported operand types.
- `__ne__` is derived from `__eq__` automatically — don't write it.
- Define `__eq__` ⇒ `__hash__` becomes `None` unless you set it.
- `bool(x)` → `__bool__`, else `__len__`, else `True`.
- `@functools.total_ordering` fills in the missing three comparisons.

## 4. Attribute access — the one that trips people

| Dunder | Called |
|---|---|
| `__getattribute__` | on **every** attribute access. Override with extreme care (infinite recursion if you touch `self.x` inside) |
| `__getattr__` | only when normal lookup **fails** — the safe hook |
| `__setattr__` | on every assignment (use `object.__setattr__` inside to avoid recursion) |
| `__delattr__` | on `del x.attr` |
| `__dir__` | `dir(x)` — make proxies introspectable |

```python
class Box:
    def __init__(self, data): object.__setattr__(self, "_data", data)  # bypass our own hook
    def __getattr__(self, name):        # fires only for names not found normally
        try: return self._data[name]
        except KeyError: raise AttributeError(name) from None   # AttributeError, not KeyError!
    def __setattr__(self, name, value): raise AttributeError("immutable")
```

Raising `AttributeError` from `__getattr__` is not optional: `hasattr`, `copy`, `pickle`
and `inspect` all probe for dunder names and expect `AttributeError` when absent.

**The infinite-recursion trap.** `copy.deepcopy(obj)` and `pickle.loads` build an instance
*without calling `__init__`*, then probe it for `__deepcopy__`/`__setstate__`. At that
moment your backing attribute doesn't exist yet — so `self._data` inside `__getattr__`
fails lookup, calls `__getattr__` again, and you get a `RecursionError` that looks like it
came from nowhere. Always guard first:

```python
def __getattr__(self, name):
    if name.startswith("_"):
        raise AttributeError(name)      # bail out before touching self.<anything>
    ...
```

## 5. Containers

| Dunder | Enables |
|---|---|
| `__len__` | `len()`, truthiness |
| `__getitem__` / `__setitem__` / `__delitem__` | `x[k]`, `x[k] = v`, `del x[k]` |
| `__contains__` | `in` (falls back to iterating with `__iter__`, then to `__getitem__`) |
| `__iter__` / `__next__` | `for`, unpacking (module 06) |
| `__reversed__` | `reversed()` |
| `__missing__` | **`dict` subclasses only**, on a failed `d[k]` — how `defaultdict` works |
| `__length_hint__` | a size *estimate* for pre-allocation |

`__getitem__` receives a `slice` object for `x[1:5]` — handle both `int` and `slice` if
you want slicing.

## 6. Operators

```
+  __add__      -  __sub__      *  __mul__      @  __matmul__
/  __truediv__  // __floordiv__ %  __mod__      ** __pow__
<< __lshift__   >> __rshift__   &  __and__      |  __or__       ^  __xor__
-x __neg__      +x __pos__      ~x __invert__   abs() __abs__
```

Three variants of each:

| Form | When |
|---|---|
| `__add__(self, other)` | `a + b` |
| `__radd__(self, other)` | `a + b` where `a` doesn't know how — **this is how `2 * money` works** |
| `__iadd__(self, other)` | `a += b`; mutate and `return self`, or omit and let `__add__` handle it |

Numeric conversions: `__int__`, `__float__`, `__complex__`, `__index__` (required for
`list[x]`, `hex(x)`, `range(x)`), `__round__`, `__trunc__`, `__floor__`, `__ceil__`.

## 7. Callables, context, async

| Dunder | Enables |
|---|---|
| `__call__` | `obj(...)` — stateful "functions", decorator classes |
| `__enter__` / `__exit__` | `with` (module 05) |
| `__aenter__` / `__aexit__` | `async with` (module 11) |
| `__aiter__` / `__anext__` | `async for` |
| `__await__` | `await obj` |

## 8. Copying and serialisation

`__copy__`, `__deepcopy__(memo)`, `__reduce__`, `__reduce_ex__`, `__getstate__`,
`__setstate__`, `__getnewargs__`. Implement `__getstate__`/`__setstate__` when your object
holds sockets, file handles, or caches that must not be pickled.

## 9. Class-level and typing

`__class_getitem__` (makes `MyClass[int]` legal), `__instancecheck__` /
`__subclasshook__` (custom `isinstance` — how ABCs and `Protocol` work),
`__mro_entries__`, `__slots__`.

## Gotchas worth remembering

1. Instance-level dunders are ignored by implicit invocation.
2. Return `NotImplemented`, don't raise, for unsupported operands.
3. `__getattr__` must raise `AttributeError` — never `KeyError`.
4. `__exit__` returning a truthy value **swallows the exception**.
5. `__hash__` disappears when you define `__eq__`.
6. `__del__` may never run; don't put resource cleanup there.
7. `__iter__` returning `self` makes a one-shot iterator (module 06).

## Exercises

`exercises_04b.py`, then `pytest 04b_dunder_methods`.

## Further reading

- [Special method names](https://docs.python.org/3/reference/datamodel.html#special-method-names)
- Fluent Python (Ramalho), chapters 1, 11–16 — the best treatment of this material anywhere
