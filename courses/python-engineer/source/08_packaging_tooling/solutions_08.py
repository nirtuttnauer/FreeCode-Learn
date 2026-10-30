"""Module 08 — reference solutions."""

from __future__ import annotations

import importlib
import importlib.metadata
import tomllib
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
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return fallback  # running from a source checkout, not an install


def load_object(target: str) -> Any:
    module_name, sep, attr_path = target.partition(":")
    if not sep or not module_name or not attr_path:
        raise ValueError(f"expected 'module:attribute', got {target!r}")
    obj: Any = importlib.import_module(module_name)
    for attr in attr_path.split("."):  # supports "module:Class.method"
        obj = getattr(obj, attr)
    return obj


def find_project_root(start: Path, marker: str = "pyproject.toml") -> Path:
    start = Path(start).resolve()
    first = start if start.is_dir() else start.parent
    for candidate in [first, *first.parents]:
        if (candidate / marker).exists():
            return candidate
    raise FileNotFoundError(f"no {marker} found above {start}")


def read_dependencies(pyproject: Path, extra: str | None = None) -> list[str]:
    with Path(pyproject).open("rb") as fh:  # tomllib requires binary
        config = tomllib.load(fh)
    project = config.get("project", {})
    if extra is None:
        return list(project.get("dependencies", []))
    return list(project["optional-dependencies"][extra])  # KeyError is the documented behaviour


class _LazyModule:
    def __init__(self, name: str) -> None:
        self._lazy_name = name
        self._lazy_module: Any = None

    def _load(self) -> Any:
        if self._lazy_module is None:
            self._lazy_module = importlib.import_module(self._lazy_name)
        return self._lazy_module

    def __getattr__(self, attr: str) -> Any:
        # Private names are handled by normal lookup; guarding here prevents the
        # __getattr__ recursion trap during copy/pickle probing.
        if attr.startswith("_"):
            raise AttributeError(attr)
        return getattr(self._load(), attr)

    def __dir__(self) -> list[str]:
        return dir(self._load())

    def __repr__(self) -> str:
        state = "loaded" if self._lazy_module is not None else "not loaded"
        return f"<lazy module {self._lazy_name!r} ({state})>"


def lazy_import(name: str) -> Any:
    return _LazyModule(name)
