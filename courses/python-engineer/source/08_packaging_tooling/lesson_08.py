"""Module 08 — runnable lesson. `python 08_packaging_tooling/lesson_08.py`"""

from __future__ import annotations

import importlib
import importlib.metadata
import sys
import tomllib
from pathlib import Path

INTRO = """When you write `import json`, Python hunts through a list of folders, runs the file once,
and remembers it forever. Nearly every baffling import error is Python looking somewhere
you didn't expect."""


def import_system() -> None:
    print("\n== the import system ==")
    print(f"  sys.path[0] = {sys.path[0]!r}  (the script's directory)")
    print(f"  modules already cached: {len(sys.modules)}")

    before = "json" in sys.modules
    import json  # noqa: F401 — importing twice does not re-execute

    print(f"  'json' cached before import: {before} -> {'json' in sys.modules}")
    print(f"  a module is an object: {type(json)} at {json.__file__}")

    print("\n  python file.py   -> sys.path[0] is the file's directory")
    print("  python -m pkg.mod -> sys.path[0] is the CWD, and the package is importable")
    print("  this single difference explains most 'ImportError in the terminal only' bugs")


def dynamic_imports() -> None:
    print("\n== dynamic imports ==")
    mod = importlib.import_module("collections")
    print(f"  import_module('collections') -> {mod.__name__}")

    # The "module:attribute" convention used by entry points, gunicorn, uvicorn, celery...
    target = "collections:OrderedDict"
    module_name, _, attr = target.partition(":")
    obj = getattr(importlib.import_module(module_name), attr)
    print(f"  resolved {target!r} -> {obj}")


def package_metadata() -> None:
    print("\n== importlib.metadata ==")
    for name in ("pytest", "mypy", "definitely-not-installed"):
        try:
            print(f"  {name}: {importlib.metadata.version(name)}")
        except importlib.metadata.PackageNotFoundError:
            print(f"  {name}: not installed (fall back to '0.0.0+dev')")

    dist = importlib.metadata.distribution("pytest")
    print(f"  pytest requires: {(dist.requires or [])[:3]} ...")

    scripts = importlib.metadata.entry_points(group="console_scripts")
    names = sorted({ep.name for ep in scripts})[:6]
    print(f"  some installed console_scripts: {names}")


def reading_toml() -> None:
    print("\n== tomllib (stdlib since 3.11) ==")
    root = Path(__file__).resolve().parent.parent
    with (root / "pyproject.toml").open("rb") as fh:  # note: binary mode is required
        config = tomllib.load(fh)
    project = config["project"]
    print(f"  name={project['name']} requires-python={project['requires-python']}")
    print(f"  dev extras: {project['optional-dependencies']['dev']}")
    print(f"  ruff line-length: {config['tool']['ruff']['line-length']}")


def project_root_discovery() -> None:
    print("\n== finding the project root ==")
    here = Path(__file__).resolve()
    for candidate in [here.parent, *here.parents]:
        if (candidate / "pyproject.toml").exists():
            print(f"  walked up from {here.name} and found: {candidate}")
            break
    print("  never hard-code '../..' — walk up looking for a marker file")


def lazy_module_attributes() -> None:
    print("\n== PEP 562: module-level __getattr__ ==")
    print("""  def __getattr__(name):
      if name == "heavy":
          import heavy            # paid only when someone touches mod.heavy
          return heavy
      raise AttributeError(name)""")
    print("  keeps `import yourpkg` fast when a submodule pulls in numpy/torch")


def resources() -> None:
    print("\n== importlib.resources ==")
    print("  files('mypkg.data').joinpath('schema.json').read_text()")
    print("  works from a wheel, a zipapp, and a source checkout — __file__ arithmetic does not")


if __name__ == "__main__":
    print(INTRO)
    import_system()
    dynamic_imports()
    package_metadata()
    reading_toml()
    project_root_discovery()
    lazy_module_attributes()
    resources()
