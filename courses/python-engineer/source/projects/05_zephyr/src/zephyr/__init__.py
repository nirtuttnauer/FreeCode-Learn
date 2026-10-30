"""zephyr — an ASGI web framework, written from scratch.

The whole framework is one idea repeated: read the handler's type hints ONCE at
registration, build a plan for where each argument comes from, then execute that plan per
request. Everything else — validation, DI, OpenAPI — falls out of the same analysis.
"""

from __future__ import annotations

__all__ = [
    "Depends",
    "HTTPException",
    "JSONResponse",
    "Request",
    "Response",
    "Zephyr",
    "__version__",
]

__version__ = "0.1.0"

from zephyr.app import Zephyr
from zephyr.di import Depends
from zephyr.exceptions import HTTPException
from zephyr.requests import Request
from zephyr.responses import JSONResponse, Response
