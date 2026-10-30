# 12 — Metaprogramming: descriptors, `__init_subclass__`, metaclasses

Code that writes code. Every ORM, every serialisation library, every framework you use is
built out of the four tools below. You need them rarely — but when you need them, nothing
else will do.

**Order of preference** (reach for the *simplest* thing that works):

1. A plain function or decorator
2. `__init_subclass__` / `__set_name__`
3. A descriptor
4. A class decorator
5. A metaclass ← almost never

## In plain English

This module is about **code that writes code**.

Normally you write a class by typing it out. But a class is just an object, created at
runtime, and you can intercept that creation and change it — or build classes from scratch
with no `class` statement at all.

Why would anyone want that? Because it's how every framework you've ever used works.
When you write a Django model or a pydantic model and suddenly get validation, database
columns and a nice `repr` you never wrote — that's this. Somebody wrote code that inspects
your class and fills in the rest.

The two ideas worth having:

- A **descriptor** is an attribute with a brain. Instead of `self.age` just storing a
  number, it can run your code on every read and write — validating, converting, logging.
  That's all `@property` is, and you can build your own.
- **`__init_subclass__`** lets a base class get notified whenever anyone subclasses it —
  which is how plugins register themselves automatically just by existing.

**Watch out for:** this is the most over-used feature in Python. The rule is at the top of
the module: reach for the *simplest* tool that works, and reach for metaclasses basically
never. Clever code is code your colleagues can't debug at 3am.

## 1. Descriptors

Any object defining `__get__` / `__set__` / `__delete__`, used as a **class attribute**.
`property`, `classmethod`, `staticmethod` and functions themselves are all descriptors.

```python
class Positive:
    def __set_name__(self, owner, name):      # called at class creation: free name binding
        self._name = f"_{name}"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self                        # accessed on the CLASS, not an instance
        return getattr(obj, self._name)

    def __set__(self, obj, value):
        if value <= 0:
            raise ValueError(f"{self._name[1:]} must be positive")
        setattr(obj, self._name, value)

class Order:
    quantity = Positive()      # one reusable validator, any number of fields
```

**Data vs non-data descriptor**: one with `__set__` or `__delete__` is a *data* descriptor
and **takes precedence over the instance `__dict__`**. Without `__set__` (e.g.
`cached_property`), the instance dict wins — which is exactly how caching-by-overwrite works.

Full attribute lookup order for `obj.x`:
1. data descriptor on the type
2. `obj.__dict__["x"]`
3. non-data descriptor / class attribute
4. `__getattr__`

## 2. `__init_subclass__` — the 90% case

```python
class Plugin:
    registry: dict[str, type] = {}

    def __init_subclass__(cls, /, name: str | None = None, **kwargs):
        super().__init_subclass__(**kwargs)     # always cooperate
        cls.registry[name or cls.__name__.lower()] = cls

class CsvPlugin(Plugin, name="csv"): ...        # class keyword arguments land here
```

This replaces the majority of metaclasses ever written: auto-registration, subclass
validation, and injecting attributes. It's an implicit classmethod — no `@classmethod`
needed.

## 3. Class decorators

```python
def add_repr(cls):
    def __repr__(self):
        fields = ", ".join(f"{k}={v!r}" for k, v in vars(self).items())
        return f"{cls.__name__}({fields})"
    cls.__repr__ = __repr__
    return cls
```

`@dataclass` is exactly this: a class decorator that reads `__annotations__` and writes
methods with `exec`. Class decorators compose; metaclasses conflict.

## 4. Metaclasses

A metaclass is the *type of a class*. `type` is the default.

```python
class Meta(type):
    def __new__(mcls, name, bases, namespace, **kwargs):
        namespace["created_by"] = "Meta"
        return super().__new__(mcls, name, bases, namespace)

class Thing(metaclass=Meta): ...
```

Legitimate uses: enforcing invariants across an entire hierarchy at definition time,
controlling `__prepare__` (the namespace mapping used during class body execution — how
`enum` detects duplicate members), customising `isinstance` via `__instancecheck__`
(how ABCs work).

The cost: metaclass conflicts in multiple inheritance, opaque tracebacks, and tooling
that can't follow your code. If `__init_subclass__` can do it, use that.

> "Metaclasses are deeper magic than 99% of users should ever worry about. If you wonder
> whether you need them, you don't." — Tim Peters

## 5. Dynamic class and function creation

```python
Klass = type("Klass", (Base,), {"field": 1, "method": lambda self: 42})
```

`types.SimpleNamespace`, `types.new_class`, `functools.partial`, and closures cover most
"I need to generate this dynamically" cases without any of the above.

## 6. Introspection toolkit

```python
inspect.signature(f), inspect.getsource(f), inspect.getmembers(obj, predicate)
inspect.isclass / isfunction / iscoroutinefunction / ismethod
vars(obj), dir(obj), type(obj).__mro__, obj.__class__
typing.get_type_hints(f)        # resolves string annotations — use THIS, not __annotations__
```

`typing.get_type_hints` is what you want in a framework: with
`from __future__ import annotations` every annotation is a string, and raw
`__annotations__` gives you `"int"` rather than `int`.

## 7. When metaprogramming is the wrong answer

If the result is code where "go to definition" fails, where a reader can't tell which
method runs, or where a typo produces silence instead of an error — you've traded a little
typing for a lot of debugging. Explicit beats clever.

## Exercises

`exercises_12.py`, then `pytest 12_metaprogramming`.

## Further reading

- [Descriptor HowTo Guide](https://docs.python.org/3/howto/descriptor.html) — read it twice
- [PEP 487 — `__init_subclass__` and `__set_name__`](https://peps.python.org/pep-0487/)
