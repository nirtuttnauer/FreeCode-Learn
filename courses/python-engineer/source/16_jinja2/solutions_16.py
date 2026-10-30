"""Module 16 — reference solutions."""

from __future__ import annotations

from typing import Any

from jinja2 import DictLoader, Environment, StrictUndefined, select_autoescape
from jinja2.sandbox import SandboxedEnvironment


def _currency(value: float) -> str:
    return f"${value:,.2f}"


def _pluralise(count: int, singular: str, plural: str | None = None) -> str:
    word = singular if count == 1 else (plural or f"{singular}s")
    return f"{count} {word}"


def _overdue(task: Any) -> bool:
    return getattr(task, "days_left", 0) < 0


def _configure(env: Environment) -> Environment:
    env.filters["currency"] = _currency
    env.filters["pluralise"] = _pluralise
    env.tests["overdue"] = _overdue
    env.globals["site_name"] = "Python Engineer"
    return env


def build_environment(templates: dict[str, str]) -> Environment:
    return _configure(
        Environment(
            loader=DictLoader(templates),
            autoescape=select_autoescape(["html", "xml"]),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )
    )


def render_string(source: str, **context: Any) -> str:
    return build_environment({}).from_string(source).render(**context)


def render_invoice(env: Environment, customer: str, lines: list[dict[str, Any]]) -> str:
    # `namespace()` is how you accumulate across loop iterations in Jinja: a plain
    # `{% set %}` inside a for-loop is scoped to that iteration and would reset each time.
    template = env.from_string(
        "INVOICE for {{ customer }}\n"
        "================\n"
        "{% set ns = namespace(total=0) %}"
        "{% for line in lines %}"
        "{% set line_total = line.quantity * line.unit_price %}"
        "{% set ns.total = ns.total + line_total %}"
        "{{ line.name }} x{{ line.quantity }} @ {{ line.unit_price | currency }}"
        " = {{ line_total | currency }}\n"
        "{% else %}"
        "(no items)\n"
        "{% endfor %}"
        "----------------\n"
        "TOTAL: {{ ns.total | currency }}\n"
        "{{ lines | length | pluralise('line') }}"
    )
    return template.render(customer=customer, lines=lines)


TEMPLATES: dict[str, str] = {
    "base.html": (
        "<html>\n"
        "<head><title>{% block title %}{{ site_name }}{% endblock %}</title></head>\n"
        "<body>{% block content %}{% endblock %}</body>\n"
        "</html>"
    ),
    "page.html": (
        '{% extends "base.html" %}\n'
        "{% block title %}{{ heading }} · {{ super() }}{% endblock %}\n"
        "{% block content %}\n"
        "<h1>{{ heading }}</h1>\n"
        '{% include "items.html" %}\n'
        "{% endblock %}"
    ),
    "items.html": (
        "<ul>\n"
        "{% for item in items %}\n"
        "<li>{{ item.name }}</li>\n"
        "{% else %}\n"
        "<li>empty</li>\n"
        "{% endfor %}\n"
        "</ul>"
    ),
    "macros.html": (
        "{% macro badge(text, kind='info') -%}\n"
        '<span class="badge badge-{{ kind }}">{{ text }}</span>\n'
        "{%- endmacro %}"
    ),
}


def render_page(heading: str, items: list[Any]) -> str:
    env = build_environment(TEMPLATES)
    return env.get_template("page.html").render(heading=heading, items=items)


def render_badge(text: str, kind: str = "info") -> str:
    env = build_environment(TEMPLATES)
    template = env.from_string(
        '{% import "macros.html" as ui %}{{ ui.badge(text, kind) }}'
    )
    return template.render(text=text, kind=kind).strip()


def render_untrusted(source: str, **context: Any) -> str:
    env = _configure(SandboxedEnvironment(autoescape=True, undefined=StrictUndefined))
    return env.from_string(source).render(**context)
