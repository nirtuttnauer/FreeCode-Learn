# Projects — the extreme track

Modules 01–17 taught the language and the practice. These five projects are where you find
out whether you actually own it. Each one is a **library or service you'd be happy to put
on GitHub**, not an exercise.

Every project ships with:

- `SPEC.md` — the full specification: milestones, required public API, acceptance criteria
- a starter package skeleton with typed stubs
- `test_acceptance.py` — a real test suite that fails until you've built it

There are **no reference solutions here.** That is the point. You have the spec, the tests,
and 17 modules of technique.

## The five

| # | Project | Build | Modules it forces you to own |
|---|---|---|---|
| 01 | **agentkit** | A multi-agent orchestration library: tools, typed schemas, planner loop, message bus, budgets, retries, tracing | 03, 04b, 07, 11, 12, 14, 17 |
| 02 | **tensorlab** | An autograd engine and neural-net framework — your own miniature PyTorch | 01, 04b, 06, 12, 13 |
| 03 | **pulse** | A production-grade FastAPI service: layered, typed, migrated, templated, instrumented | 05, 07, 09, 14, 15, 16, 17 |
| 04 | **forge** | A durable task queue and scheduler with at-least-once delivery, retries, backpressure | 05, 06, 10, 11, 13, 17 |
| 05 | **zephyr** | A from-scratch ASGI web framework — routing, DI, validation, middleware | 04b, 06, 07, 11, 12, 14 |

**Suggested order**: 02 → 05 → 03 → 04 → 01. `tensorlab` is self-contained and pure
algorithm; `zephyr` teaches you what `pulse` is standing on; `forge` and `agentkit` are the
hardest because they're concurrent *and* stateful.

Pick one and finish it. A finished project beats three half-built ones — every time,
in learning and in interviews.

## Running a project

Project tests are excluded from `make test` (they'd be red until you build them). Run one
explicitly:

```bash
make project P=02          # or: .venv/bin/pytest projects/02_tensorlab -o addopts=""
```

## The engineering bar

Every project is expected to meet all of this, not just pass its tests:

- [ ] `src/` layout, installable with `pip install -e .`, real `pyproject.toml`
- [ ] `ruff check` and `ruff format` clean
- [ ] `mypy --strict` clean on the package (test files may be looser)
- [ ] ≥ 85% test coverage, and the tests are fast (< 10s for the whole suite)
- [ ] A README with a 10-line quickstart that actually works from a fresh clone
- [ ] Public API exported through `__init__.py` with `__all__`; internals prefixed `_`
- [ ] Custom exception hierarchy with one base class
- [ ] No `print` in library code — `logging` only
- [ ] Dependencies injected, not imported at point of use; one composition root
- [ ] Type hints everywhere, including generics where they carry meaning
- [ ] A CHANGELOG and a version, read via `importlib.metadata`

## How to work on one

1. Read `SPEC.md` end to end before writing a line.
2. Run `test_acceptance.py` and watch it fail. That's your definition of done.
3. Build milestone by milestone — each is designed to be a working, committable state.
4. Write your OWN tests as you go; the acceptance suite is a floor, not a ceiling.
5. When it passes, do the "going further" section. That's where the interesting part is.

## Grading yourself

| Level | What it looks like |
|---|---|
| **Pass** | acceptance tests green |
| **Good** | + the engineering bar above, + your own tests, + a real README |
| **Strong** | + one "going further" item, + benchmarks or a design doc explaining trade-offs |
| **Portfolio** | + published to PyPI or deployed, + CI, + docs someone else could use |
