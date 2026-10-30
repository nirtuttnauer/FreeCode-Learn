"""Module 08 exercises.  pytest 08_packaging_tooling

The runtime half of packaging: metadata, entry points, project discovery, TOML, and
lazy imports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = [
    "find_project_root",
    "lazy_import",
    "load_object",
    "package_version",
    "read_dependencies",
]


def package_version(name: str, fallback: str = "0.0.0+dev") -> str:
    """Return the installed version of `name`, or `fallback` when it isn't installed.

    Use `importlib.metadata.version` and catch `PackageNotFoundError` — this is the exact
    snippet that belongs at the top of every `__init__.py` you write.
    """
    raise NotImplementedError


def load_object(target: str) -> Any:
    """Resolve a "module.path:attribute" string into the object itself.

    >>> load_object("collections:OrderedDict").__name__
    'OrderedDict'
    >>> load_object("json:dumps")({"a": 1})
    '{"a": 1}'

    This is the convention entry points, uvicorn, gunicorn and celery all use.

    - Dotted attributes work too: "module:Class.method".
    - A missing colon raises ValueError("expected 'module:attribute', got ...").
    - An unimportable module raises ImportError (let `import_module` do it).
    - A missing attribute raises AttributeError.
    """
    raise NotImplementedError


def find_project_root(start: Path, marker: str = "pyproject.toml") -> Path:
    """Walk up from `start` until a directory containing `marker` is found; return it.

    - `start` may be a file or a directory.
    - Raise FileNotFoundError if the filesystem root is reached without a match.

    Every real CLI needs this. Nobody should ever write `Path(__file__).parent.parent.parent`.
    """
    raise NotImplementedError


def read_dependencies(pyproject: Path, extra: str | None = None) -> list[str]:
    """Read dependency strings out of a pyproject.toml.

    - `extra=None` -> `[project].dependencies`
    - `extra="dev"` -> `[project.optional-dependencies].dev`
    - Missing sections return `[]` rather than raising.
    - A missing FILE raises FileNotFoundError.
    - A requested extra that doesn't exist raises KeyError.

    Use `tomllib` — and remember it needs the file opened in BINARY mode.
    """
    raise NotImplementedError


def lazy_import(name: str) -> Any:
    """Return a proxy that imports `name` only when an attribute is first touched.

    >>> json = lazy_import("json")      # nothing imported yet
    >>> json.dumps({"a": 1})            # NOW it imports
    '{"a": 1}'

    Requirements:
    - The module must NOT be in `sys.modules` right after `lazy_import(...)` returns
      (assuming it wasn't already imported).
    - The import happens at most once, no matter how many attributes are accessed.
    - A bad module name raises ImportError on first attribute access, not before.
    - `repr(proxy)` is "<lazy module 'json' (not loaded)>" before loading and
      "<lazy module 'json' (loaded)>" after.

    Build a small class with `__getattr__` (module 04b). Be careful: storing state on
    `self` inside a class whose `__getattr__` fetches from the module is exactly the
    recursion trap from that module — set your private attributes in `__init__` and
    guard names starting with "_".
    """
    raise NotImplementedError
