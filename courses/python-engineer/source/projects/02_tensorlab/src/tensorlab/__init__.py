"""tensorlab — a miniature autograd engine and neural-network framework.

Start with `engine.py` (milestone 1). Everything else builds on it.
"""

from __future__ import annotations

__all__ = ["Value", "__version__"]

__version__ = "0.1.0"

from tensorlab.engine import Value
