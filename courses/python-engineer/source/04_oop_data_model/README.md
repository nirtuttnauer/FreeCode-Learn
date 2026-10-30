# 04 — OOP and the data model

Python's OOP is not Java's. There are no interfaces, no private members, and no
overloading. What there *is* instead: the **data model** — a set of dunder methods the
interpreter calls on your behalf. Implement the right ones and your object plugs into
every builtin, operator and syntax form.

## In plain English

In a lot of languages, objects are just bundles of data with functions attached. Python's
version is more interesting: your object can **plug into the language itself**.

Python has a set of specially-named methods (they all look like `__this__`, and people say
"dunder" for "double underscore"). If you write the right one, normal Python syntax starts
working on your object:

- write `__len__` and `len(your_thing)` works
- write `__add__` and `your_thing + other` works
- write `__eq__` and `==` works

You're not overriding some framework — you're teaching Python what your object *means*.
That's why a well-written Python class feels like it was built into the language.

The other half of this module is **dataclasses**: a way to say "this class just holds these
four fields" and get the constructor, the printing, and the equality checks written for you,
for free, in one line.

**Watch out for:** the moment you define `__eq__`, Python silently removes your object's
ability to go in a `set` or be a dict key, unless you also define `__hash__`. That's
deliberate, and the lesson explains why.

## 1. The protocols that matter

| You want | Implement | Enables |
|---|---|---|
| A useful repr | `__repr__` (always), `__str__` (optional) | debugger, logs, REPL |
| Equality | `__eq__` (+ `__hash__`) | `==`, `in`, dict keys, sets |
| Ordering | `__lt__` + `@total_ordering`, or all six | `sorted`, `min`, `<` |
| Arithmetic | `__add__`, `__radd__`, `__iadd__`, `__mul__`, `__neg__`, `__abs__` | operators |
| Container | `__len__`, `__getitem__`, `__setitem__`, `__contains__`, `__iter__` | `len`, `x[i]`, `in`, `for` |
| Callable | `__call__` | `obj()` |
| Context manager | `__enter__`, `__exit__` | `with` (module 05) |
| Attribute magic | `__getattr__`, `__getattribute__`, `__setattr__` | proxies, lazy loading (module 12) |
| Formatting | `__format__` | `f"{obj:spec}"` |

`__repr__` should be unambiguous and ideally `eval`-able: `Point(x=1, y=2)`. `__str__`
falls back to `__repr__`, so if you only write one, write `__repr__`.

## 2. `__eq__` and `__hash__` travel together

Define `__eq__` and Python sets `__hash__ = None` — your object becomes unhashable.
Rules:

- Equal objects **must** have equal hashes.
- Only hash on **immutable** parts. Hashing a mutable field and then mutating it corrupts
  every set/dict holding the object.
- Mutable value object → define `__eq__`, leave it unhashable. That's correct, not a bug.

```python
def __eq__(self, other: object) -> bool:
    if not isinstance(other, Money):
        return NotImplemented          # NOT False — lets the other side try
    return (self.amount, self.currency) == (other.amount, other.currency)

def __hash__(self) -> int:
    return hash((self.amount, self.currency))
```

Returning `NotImplemented` (the singleton, not the exception) tells Python "try the
reflected operation", which is how `1 + MyNum()` can work via `__radd__`.

## 3. Dataclasses

```python
from dataclasses import dataclass, field

@dataclass(frozen=True, slots=True, kw_only=True, order=True)
class Money:
    amount: Decimal
    currency: str = "USD"
    tags: list[str] = field(default_factory=list, compare=False, repr=False)

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("negative")     # on frozen: object.__setattr__ to assign
```

| Option | Effect |
|---|---|
| `frozen=True` | immutable + hashable (assignment raises `FrozenInstanceError`) |
| `slots=True` | no `__dict__`; less memory, faster attribute access (3.10+) |
| `kw_only=True` | all fields keyword-only — makes adding fields non-breaking |
| `order=True` | generates `<`, `<=`, `>`, `>=` from field order |
| `eq=False` | keep identity-based equality |

`field(default_factory=list)` is the dataclass answer to the mutable-default trap — a bare
`= []` is a `ValueError` at class creation.

**Choosing**: `NamedTuple` for tiny immutable records that should behave like tuples;
`@dataclass` for most value/config objects; `pydantic.BaseModel` when you need *runtime*
validation and parsing from untrusted input (module 15 uses it heavily).

## 4. Properties

```python
class Celsius:
    def __init__(self, degrees: float) -> None:
        self.degrees = degrees          # goes through the setter — validation from day one
    @property
    def degrees(self) -> float:
        return self._degrees

    @degrees.setter
    def degrees(self, value: float) -> None:
        if value < -273.15:
            raise ValueError("below absolute zero")
        self._degrees = value

    @property
    def fahrenheit(self) -> float:      # computed, read-only
        return self._degrees * 9 / 5 + 32
```

Start with a plain attribute. Promote it to a property *when* you need validation or
computation — the call site never changes. That's why Python has no getters/setters by
convention.

`property` is itself a descriptor; module 12 shows how to build your own.

## 5. Inheritance, MRO, `super()`

`super()` does **not** mean "my parent". It means "the next class in the MRO of
`type(self)`" — which depends on the *instance*, not the defining class. That's what makes
cooperative multiple inheritance and mixins work.

```python
Klass.__mro__          # the linearisation (C3)
super().__init__(**kwargs)   # cooperative: pass along what you don't consume
```

Rules of thumb:
- Prefer composition. Inherit for **is-a** and for framework hooks.
- Mixins go **left** of the base class: `class Service(LoggingMixin, Base)`.
- Every cooperative `__init__` should accept and forward `**kwargs`.
- `isinstance` checks against `abc`/`Protocol` beat concrete classes (modules 07, 14).

## 6. Class vs instance vs static

```python
class Widget:
    registry: ClassVar[list[str]] = []      # shared by ALL instances — mutation is global
    def method(self): ...                   # bound to instance
    @classmethod
    def from_json(cls, raw): ...            # alternative constructor; `cls` respects subclasses
    @staticmethod
    def validate(raw): ...                  # namespaced function, no self/cls
```

`@classmethod` is the idiomatic way to write alternative constructors — and it does the
right thing under inheritance.

## 7. Privacy conventions

- `_name` — "internal, don't touch". Enforced by nothing but professionalism.
- `__name` — **name mangling** to `_ClassName__name`; use it only to avoid collisions in
  inheritance hierarchies, not as security.
- `__all__` in a module controls `from mod import *` and signals public API.

## Exercises

`exercises_04.py`, then `pytest 04_oop_data_model`.

### Warmups (Gentle ramp-up)
1. **`Point2D`**: Basic dunders (`__repr__`, `__str__`, `__eq__`, `__add__`, `__sub__`, `__mul__`, `__abs__`).
2. **`Rectangle`**: Properties with validation and computed attributes (`.area`, `.perimeter`).
3. **`BankAccount`**: Invariants, transaction methods, deposit/withdrawal validation, and string formatting.
4. **`Multiplier`**: The callable protocol (`__call__`).
5. **`Playlist`**: Sequence container protocol (`__len__`, `__getitem__`, `__iter__`, `__contains__`).
6. **`Color`**: Value object with range validation, `__eq__`, `__hash__`, and `.hex_code` property.
7. **`InventoryItem`**: Simple `@dataclass`, default values, `default_factory`, methods.
8. **`HighScore`**: Comparison and `@total_ordering` with `__lt__` and `__eq__`.
9. **`Percentage`**: Formatting protocol (`__format__`), `__str__`, and `__float__`.
10. **`Employee`**: Class variables vs instance variables, auto-incrementing ID.
11. **`Person`**: Alternative constructors with `@classmethod` (`from_full_name`, `from_dict`).
12. **`Circle` & `Square`**: Inheritance and polymorphism subclassing `Shape`.
13. **`TagSet`**: Operator overloading for sets (`__or__`, `__and__`, `__sub__`).
14. **`StepCounter`**: In-place operators (`__iadd__`) and type conversion (`__int__`, `__bool__`).

### Advanced
15. **`Money`**: Frozen dataclass combining total ordering, currency validation, Decimal coercion, operator overloading.
16. **`Temperature`**: Properties with validation, computed scales, classmethod alternative constructor, custom equality & hash.
17. **`CircularBuffer`**: Fixed-capacity FIFO wrapping `collections.deque` with eviction tracking and container protocol.
18. **`CaseInsensitiveDict`**: Complete mapping subclassing `collections.abc.MutableMapping`.

## Further reading

- [Data model reference](https://docs.python.org/3/reference/datamodel.html#special-method-names)
- [`dataclasses`](https://docs.python.org/3/library/dataclasses.html)
- Raymond Hettinger, *Super considered super!*
