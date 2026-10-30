"""Module 16 exercises.  pytest 16_jinja2"""

from __future__ import annotations

from typing import Any

from jinja2 import Environment


def build_environment(templates: dict[str, str]) -> Environment:
    """Return a properly configured Environment backed by an in-memory template dict.

    Required configuration:
    - `DictLoader(templates)`
    - autoescape ON for .html and .xml (use `select_autoescape`)
    - `undefined=StrictUndefined` — a missing variable must raise, not render ""
    - `trim_blocks=True` and `lstrip_blocks=True`

    Required extensions:
    - filter `currency`: 1234.5 -> "$1,234.50"
    - filter `pluralise`: `pluralise(n, "file")` -> "1 file" / "2 files";
      an optional third argument overrides the plural: `pluralise(2, "box", "boxes")`
    - test `overdue`: true when a task-like object's `.days_left` is negative
    - global `site_name` = "Python Engineer"
    """
    raise NotImplementedError


def render_string(source: str, **context: Any) -> str:
    """Render a template string with the same configuration as `build_environment`.

    Handy for one-offs and tests. Reuse `build_environment({})` — don't duplicate the
    config, and don't build a new Environment per call in real code (it caches compiled
    templates).
    """
    raise NotImplementedError


def render_invoice(env: Environment, customer: str, lines: list[dict[str, Any]]) -> str:
    """Render a plain-text invoice from `lines` (each: name, quantity, unit_price).

    Exact expected output for
    `[{"name": "Widget", "quantity": 2, "unit_price": 9.5}]` and customer "ACME":

        INVOICE for ACME
        ================
        Widget x2 @ $9.50 = $19.00
        ----------------
        TOTAL: $19.00
        1 line

    Rules:
    - One line per item, in input order: "<name> x<qty> @ <unit|currency> = <total|currency>"
    - The "=" and "-" rules are exactly 16 characters.
    - TOTAL is the sum of the line totals, through the `currency` filter.
    - The final line uses your `pluralise` filter: "1 line" / "3 lines".
    - No trailing newline.
    - With no lines at all, the body is the single line "(no items)" and the total is $0.00.

    Do the arithmetic in the TEMPLATE (`{% set %}`, `loop`, filters) rather than in
    Python — the point is to get fluent with the template language.
    """
    raise NotImplementedError


TEMPLATES: dict[str, str] = {
    # Fill these in. The tests render "page.html" and check the result.
    #
    # base.html   — an HTML skeleton with a `title` block (defaulting to the `site_name`
    #               global) and a `content` block.
    # page.html   — extends base.html, overrides `title` with "{{ heading }} · " plus the
    #               parent title via super(), and fills `content` with an <h1> of
    #               `heading` followed by an include of "items.html".
    # items.html  — a <ul> of `items`, each "<li>{{ item.name }}</li>", or a single
    #               "<li>empty</li>" when there are none (use the for/else form).
    # macros.html — a `badge(text, kind="info")` macro rendering
    #               '<span class="badge badge-{{ kind }}">{{ text }}</span>'.
}


def render_page(heading: str, items: list[Any]) -> str:
    """Render "page.html" from TEMPLATES with the given context, and return the HTML.

    The tests check: the heading appears in an <h1>, every item name appears in an <li>,
    the empty case renders "empty", the <title> contains both the heading and the site
    name, and — importantly — that a hostile item name is ESCAPED, not injected.
    """
    raise NotImplementedError


def render_badge(text: str, kind: str = "info") -> str:
    """Import the `badge` macro from "macros.html" and render it. Output is escaped HTML."""
    raise NotImplementedError


def render_untrusted(source: str, **context: Any) -> str:
    """Render a template supplied by an UNTRUSTED user.

    Use `jinja2.sandbox.SandboxedEnvironment`, with autoescaping on. A template that
    reaches for `__class__`, `__globals__`, `__subclasses__` etc. must raise
    `jinja2.exceptions.SecurityError`, not leak the interpreter's internals.

    This is the difference between a template feature and a remote code execution bug.
    """
    raise NotImplementedError
