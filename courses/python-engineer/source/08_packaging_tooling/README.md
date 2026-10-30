# 08 — Modules, packaging, project tooling

This is the module that makes your code *shippable* rather than *a folder of scripts*.

## In plain English

This is the module that turns "a folder of Python files on my laptop" into "a thing another
human being can install and use".

The difference is mostly boring and mostly conventions: where files go, one config file that
describes your project, and a way to say "this project needs these libraries at these
versions". Boring, but it's the difference between a hobby script and something you can ship,
deploy, or hand to a colleague.

The mental model for **imports**: when you write `import json`, Python goes hunting through a
list of folders for something called `json`, runs it once, and remembers the result forever.
Nearly every confusing import error is Python looking in a different set of folders than you
expected.

**Watch out for:** `python myfile.py` and `python -m mypackage.myfile` search *different*
places. That single difference is behind most "it works in my editor but not in the
terminal" bugs.

## 1. Import mechanics

- A **module** is a `.py` file. A **package** is a directory with `__init__.py`
  (a *namespace package* omits it — fine for plugin namespaces, confusing otherwise).
- `import x` executes the module **once**; the result is cached in `sys.modules`.
  Re-importing does nothing. That's why module-level code is effectively a singleton.
- Import resolution walks `sys.path`: script dir (or cwd for `-m`), then `PYTHONPATH`,
  then site-packages.
- **Always use absolute imports.** Relative imports (`from .models import User`) are fine
  *inside* a package, never at the top level.
- Circular imports: fix by moving the import into the function, or by
  `if TYPE_CHECKING:` when it's only needed for annotations.
- `python -m package.module` runs it with the package importable — `python path/file.py`
  does not. This is the cause of most "works in my IDE, breaks in the terminal" bugs.

## 2. Project layout — use `src/`

```
myproject/
├── pyproject.toml
├── README.md
├── src/
│   └── myproject/
│       ├── __init__.py
│       ├── __main__.py       # enables `python -m myproject`
│       ├── cli.py
│       ├── core.py
│       └── py.typed          # ship this so consumers get your type hints
└── tests/
    └── test_core.py
```

The `src/` layout forces you to install the package to import it, which means your tests
run against the *installed* artefact — the same thing your users get. Flat layouts silently
import from the working directory and hide packaging bugs.

## 3. `pyproject.toml` — the only config file you need

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "myproject"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["httpx>=0.27"]

[project.optional-dependencies]
dev = ["pytest", "mypy", "ruff"]

[project.scripts]
myproject = "myproject.cli:main"      # installs a `myproject` command

[project.entry-points."myproject.plugins"]
csv = "myproject.plugins.csv:Plugin"  # third parties can register here

[tool.ruff]
line-length = 100
```

Backends: **hatchling** (good default), setuptools (legacy but universal), **uv_build**,
flit, poetry-core, maturin (Rust extensions).

## 4. Environments and installers

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"       # editable install — code changes take effect immediately
```

**uv** is the current best-in-class tool (Rust, ~10–100× faster than pip):

```bash
uv venv                       # create .venv
uv pip install -e ".[dev]"    # pip-compatible interface
uv sync                       # from uv.lock — reproducible
uv run pytest                 # run in the project env without activating
uv add httpx                  # add a dependency and update the lock
uvx ruff check .              # run a tool without installing it
```

Lock your dependencies for applications (`uv.lock`, `requirements.txt` via `uv pip compile`).
Do **not** pin hard in a *library's* `pyproject.toml` — libraries declare ranges,
applications lock.

## 5. Versions and metadata at runtime

```python
from importlib.metadata import version, entry_points, PackageNotFoundError

try:
    __version__ = version("myproject")
except PackageNotFoundError:      # running from a source checkout
    __version__ = "0.0.0+dev"

for ep in entry_points(group="myproject.plugins"):
    plugin = ep.load()
```

Never hand-maintain `__version__` in two places — read it from the installed metadata, or
have the build backend read it from the code (`[tool.hatch.version] path = ...`).

## 6. Controlling your public API

```python
__all__ = ["User", "load"]        # what `from mod import *` exports; documents intent

def __getattr__(name: str):       # PEP 562: module-level lazy attributes
    if name == "heavy":
        import heavy_module
        return heavy_module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

Module `__getattr__` is how you keep import time low when one submodule pulls in numpy.

## 7. Reading files that ship with your package

Never use `__file__` arithmetic. Use `importlib.resources`:

```python
from importlib.resources import files
schema = files("myproject.data").joinpath("schema.json").read_text()
```

It works from a zip, a wheel, and a source checkout alike.

## 8. Tooling stack worth standardising on

| Tool | Replaces |
|---|---|
| **ruff** | flake8, isort, pyupgrade, pydocstyle, autoflake, black (`ruff format`) |
| **mypy** / pyright | — |
| **pytest** | unittest |
| **uv** | pip, pip-tools, virtualenv, pyenv, pipx |
| **pre-commit** | manual discipline |
| **hatch** / uv | tox, setup.py |

`tomllib` is in the stdlib since 3.11 — read TOML with no dependency (write still needs
`tomli-w`).

## 9. Publishing

```bash
uv build                       # or python -m build  -> dist/*.whl, *.tar.gz
uv publish                     # or twine upload dist/*
```

Use PyPI **trusted publishing** from CI rather than long-lived API tokens.

## Exercises

`exercises_08.py`, then `pytest 08_packaging_tooling`. They're the runtime half of this
topic: version resolution, entry-point strings, project-root discovery, TOML config, and
lazy imports.

## Further reading

- [Python Packaging User Guide](https://packaging.python.org/)
- [uv docs](https://docs.astral.sh/uv/)
- [PEP 621 — project metadata](https://peps.python.org/pep-0621/)
