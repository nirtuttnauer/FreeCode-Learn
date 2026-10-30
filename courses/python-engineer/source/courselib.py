"""Tiny test harness shared by every module.

Each module has both `exercises_NN.py` (your work) and `solutions_NN.py` (reference).
The test files import through `impl()` so the *same* test suite can grade either one:

    pytest 03_functions            # grades exercises_03.py
    SOLUTIONS=1 pytest 03_functions  # grades solutions_03.py  (sanity-checks the tests)
"""

from __future__ import annotations

import importlib
import os
from types import ModuleType


def impl(number: str) -> ModuleType:
    """Import `exercises_NN`, or `solutions_NN` when SOLUTIONS is set in the environment.

    Works because pytest (in its default `prepend` import mode) puts the directory of each
    test file at the front of `sys.path`, and every module's files are uniquely named.
    """
    prefix = "solutions" if os.environ.get("SOLUTIONS") else "exercises"
    return importlib.import_module(f"{prefix}_{number}")
