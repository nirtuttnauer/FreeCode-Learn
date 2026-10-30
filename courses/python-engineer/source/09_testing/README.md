# 09 — Testing with pytest

You already know *why* to test. This module is about pytest's actual feature set and —
more importantly — **designing code so it can be tested without ceremony**.

## In plain English

A test is a trap you set for your future self. You write down what the code *should* do, and
from then on the computer checks it for you every time you change something — including the
bit you were sure you hadn't touched.

The real skill isn't writing tests. It's **writing code that's easy to test**, and that turns
out to be the same thing as writing code that's easy to understand.

The trick that does most of the work: don't let your code reach out and grab things. If a
function needs the current time, hand it a clock instead of letting it call `time.now()`
itself. Then in a test you hand it a *fake* clock and say "it is now three hours later" — and
your test runs in a millisecond instead of waiting three hours. Same for random numbers,
sleeping, and network calls.

That's what every exercise in this module is really about.

**Watch out for:** the difference between a **fake** (a small, real, working version of
something — an in-memory database) and a **mock** (an empty puppet that just records what
you did to it). Fakes survive refactoring. Mocks tend to keep passing long after the real
code has stopped working.

## 1. The pytest model

- Test files `test_*.py`, functions `test_*`, classes `Test*` (no `__init__`).
- Plain `assert` — pytest rewrites it to give you rich failure output.
- No boilerplate base classes. A test is a function.

```bash
pytest                      # everything
pytest path/test_x.py::TestA::test_b
pytest -k "parse and not slow"   # substring/expression selection
pytest -x --lf              # stop at first failure; rerun last failures
pytest -q / -v / -s         # quiet / verbose / don't capture stdout
pytest --durations=10       # find your slow tests
```

## 2. Fixtures

```python
@pytest.fixture
def db():
    conn = connect(":memory:")
    yield conn            # everything after yield is teardown
    conn.close()

def test_insert(db):      # requested by NAME — that's the whole wiring mechanism
    ...
```

Scopes: `function` (default), `class`, `module`, `package`, `session`. Wider scope = faster
but shared state — a common source of order-dependent flakiness.

Put shared fixtures in `conftest.py`; they're discovered automatically by every test in
that directory tree, with no import.

Builtin fixtures worth memorising:

| Fixture | Use |
|---|---|
| `tmp_path` | a `Path` to a fresh temp directory |
| `monkeypatch` | patch attrs/env/cwd, auto-undone |
| `capsys` / `capfd` | capture stdout/stderr |
| `caplog` | assert on log records |
| `request` | metadata about the running test (for parametrised fixtures) |

```python
def test_env(monkeypatch):
    monkeypatch.setenv("API_KEY", "x")
    monkeypatch.setattr("myapp.client.send", lambda *a: None)
    monkeypatch.chdir(tmp_path)
```

## 3. Parametrize

```python
@pytest.mark.parametrize(("raw", "expected"), [("1h", 3600), ("90s", 90)])
def test_parse(raw, expected):
    assert parse_duration(raw) == expected
```

Stack decorators for a cartesian product. Parametrise **fixtures** to run the whole suite
against several backends:

```python
@pytest.fixture(params=["memory", "sqlite"])
def repo(request): ...
```

## 4. Exceptions, warnings, approximations

```python
with pytest.raises(ValueError, match="port"):     # match is a regex on str(exc)
    parse(...)

with pytest.raises(ExceptionGroup) as info:
    ...
assert len(info.value.exceptions) == 3

assert 0.1 + 0.2 == pytest.approx(0.3)
with pytest.warns(DeprecationWarning): ...
```

## 5. Markers

```python
@pytest.mark.slow
@pytest.mark.skipif(sys.platform == "win32", reason="posix only")
@pytest.mark.xfail(strict=True, reason="known bug #123")
```

Declare markers in `pyproject.toml` (`--strict-markers` makes typos fail loudly), then
`pytest -m "not slow"`.

## 6. Mocking — and why you should need it rarely

```python
from unittest.mock import Mock, patch

client = Mock(spec=ApiClient)          # spec => attribute typos raise
client.fetch.return_value = {"ok": True}
client.fetch.side_effect = [1, 2, TimeoutError]   # sequence, or an exception

client.fetch.assert_called_once_with("users")
```

Rules that keep mocks from rotting:
- **Always use `spec=`/`autospec=True`.** Without it, a `Mock` happily accepts calls to
  methods that no longer exist — a green test for deleted code.
- `patch` where the object is **looked up**, not where it's defined:
  `patch("myapp.service.requests")`, not `patch("requests")`.
- Prefer **dependency injection** to patching. A function that takes `clock`, `sleeper`,
  or a repository as a parameter needs no mock library at all — that's exactly what the
  exercises below make you do.
- Prefer a hand-written **fake** (a real in-memory implementation of a Protocol) to a mock
  when the collaborator has behaviour.

## 7. Property-based testing (hypothesis)

Example-based tests check the cases you thought of. Property tests attack the ones you
didn't:

```python
from hypothesis import given, strategies as st

@given(st.integers(min_value=1, max_value=3999))
def test_roman_roundtrip(n):
    assert roman_decode(roman_encode(n)) == n

@given(st.lists(st.integers()))
def test_sort_is_idempotent(xs):
    assert sorted(sorted(xs)) == sorted(xs)
```

Best properties to look for: **round-trip** (encode/decode), **invariant** (length is
preserved), **oracle** (matches a slow-but-obvious implementation), **idempotence**.
Hypothesis shrinks failures to a minimal counter-example and remembers it.

## 8. Coverage — a floor, not a target

```bash
pytest --cov=src --cov-report=term-missing --cov-fail-under=80
```

100% coverage with no assertions proves nothing. Use it to find *untested* code, not to
prove code is *tested*.

## 9. Test design

- **Arrange / Act / Assert**, one behaviour per test.
- Name the behaviour: `test_rejects_negative_amounts`, not `test_money_2`.
- Test the public API, not private helpers — private tests break on every refactor.
- Deterministic: no real clocks, no real network, no random without a seed, no
  inter-test order dependence.
- Fast: the suite you don't run is worthless. Mark the slow ones and exclude them locally.

## Exercises

`exercises_09.py`, then `pytest 09_testing`. Every exercise is about **injecting** the
thing that would otherwise make a test slow or flaky (time, sleep, randomness).

**Ungraded challenge, do it anyway:** write `my_tests_09.py` with your own hypothesis
property tests for `parse_duration` and `roman_encode` — round-trip and invariant
properties. Run it with `pytest 09_testing/my_tests_09.py`.

## Further reading

- [pytest docs](https://docs.pytest.org/)
- [hypothesis docs](https://hypothesis.readthedocs.io/)
