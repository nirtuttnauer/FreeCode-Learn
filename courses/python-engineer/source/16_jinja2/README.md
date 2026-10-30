# 16 — Jinja2: templating done properly

Jinja2 renders HTML, emails, config files, SQL, YAML manifests, code generators — anywhere
you'd otherwise be gluing strings together. It's also the templating language behind
Flask, Ansible, dbt, Django-adjacent tooling and FastAPI's HTML responses.

## In plain English

A template is a fill-in-the-blanks letter. You write the HTML once with gaps in it —
`Hello {{ name }}` — and hand it a name to fill in.

The thing worth genuinely caring about here is **autoescaping**, and it's a security idea,
not a formatting one.

Say a user sets their display name to `<script>steal_cookies()</script>`. If your template
drops that straight into the page, every visitor's browser will *run it*, because browsers
can't tell the difference between HTML you wrote and HTML a stranger typed into a form.
That's cross-site scripting, and it's been in the top 10 web vulnerabilities for two decades.

Autoescaping turns those dangerous characters into harmless ones automatically, so the name
displays as text instead of running as code. Jinja can do this for you on every single
variable — but only if you switch it on.

**Watch out for:** the `|safe` filter turns escaping *off* for one value. It exists for
markup you generated yourself. Using it on anything a user typed re-opens the exact hole
autoescaping just closed.

## 1. The three delimiters

```jinja
{{ expression }}      {# printed  #}
{% statement %}       {# logic: if / for / set / block / macro / include #}
{# comment #}         {# never rendered #}
```

## 2. Environment and loaders — the part people skip

```python
from jinja2 import Environment, FileSystemLoader, select_autoescape

env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"]),   # SECURITY: see §5
    undefined=StrictUndefined,                       # fail loudly on typos
    trim_blocks=True,      # a block tag swallows the newline after it
    lstrip_blocks=True,    # ...and the leading whitespace before it
)
template = env.get_template("page.html")
html = template.render(user=user, items=items)
```

Loaders: `FileSystemLoader`, `PackageLoader("mypkg", "templates")` (works from a wheel),
`DictLoader` (tests), `ChoiceLoader` (overrides). Build **one** `Environment` per app and
reuse it — it compiles and caches templates.

`Environment.from_string(...)` is fine for one-offs and tests.

## 3. Control flow

```jinja
{% for item in items %}
  {{ loop.index }}. {{ item.name }}{% if not loop.last %},{% endif %}
{% else %}
  Nothing here.        {# runs when `items` is empty — no equivalent in most languages #}
{% endfor %}

{% if user.is_admin %}...{% elif user.is_staff %}...{% else %}...{% endif %}
{% set total = items | sum(attribute="price") %}
```

`loop` gives you `index` (1-based), `index0`, `first`, `last`, `length`, `revindex`,
`cycle("odd","even")`, `previtem`/`nextitem`, and `loop.depth` for recursion.

## 4. Inheritance, includes, macros

```jinja
{# base.html #}
<html><body>{% block content %}{% endblock %}</body></html>

{# page.html #}
{% extends "base.html" %}
{% block content %}
  {{ super() }}                  {# render the parent's version too #}
  <h1>{{ title }}</h1>
{% endblock %}
```

| Tool | Use |
|---|---|
| `{% extends %}` + `{% block %}` | page layout (one parent per template) |
| `{% include "part.html" %}` | drop in a fragment with the current context |
| `{% macro %}` / `{% import %}` | reusable, parameterised components |
| `{% call %}` | pass a body into a macro |

```jinja
{% macro field(name, value="", type="text") %}
  <input name="{{ name }}" value="{{ value }}" type="{{ type }}">
{% endmacro %}
{{ field("email", user.email) }}
```

Macros are the right answer to "I keep copying this markup". Includes are for whole
fragments, inheritance for page structure.

## 5. Autoescaping — the security section

**Turn autoescaping on.** With it off, `{{ user_bio }}` containing
`<script>steal()</script>` is an XSS hole.

```python
Environment(autoescape=True)               # or select_autoescape([...])
```

- `{{ value }}` escapes `< > & " '` when autoescape is on.
- `{{ value | safe }}` marks a value as already-safe HTML — **only** for content you
  generated, never for user input.
- `markupsafe.Markup("<b>ok</b>")` is the programmatic equivalent.
- `{% autoescape false %}...{% endautoescape %}` scopes it off for e.g. plaintext email.

Never build HTML by concatenation and then pass it through `|safe`. That's the same hole
with more steps.

## 6. Filters and tests

```jinja
{{ name | upper | truncate(20) }}
{{ price | round(2) }}
{{ items | selectattr("active") | map(attribute="name") | join(", ") }}
{{ description | default("none", boolean=true) }}
{{ raw_html | striptags }}
{% if value is defined and value is not none %}
```

Custom ones are just Python functions:

```python
env.filters["currency"] = lambda v: f"${v:,.2f}"
env.tests["overdue"] = lambda task: task.due < today()
env.globals["now"] = datetime.now      # available in every template
```

That's the extension model in full: filters transform, tests answer yes/no, globals are
ambient values.

## 7. `StrictUndefined`

By default, `{{ user.naem }}` renders as an empty string — a typo becomes a silent blank
page. With `undefined=StrictUndefined` it raises `UndefinedError`. Use it everywhere
except templates that deliberately render optional data.

## 8. Async, streaming, sandboxing

- `Environment(enable_async=True)` → `await template.render_async(...)`, needed under
  FastAPI when a filter awaits.
- `template.stream(...)` / `generate()` yields chunks instead of one big string — for
  large reports and CSV exports.
- `SandboxedEnvironment` when *users* supply templates. A normal Environment lets a
  template reach `__class__`/`__globals__` and escape to arbitrary code.

## 9. With FastAPI

```python
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

@app.get("/tasks", response_class=HTMLResponse)
async def page(request: Request):
    return templates.TemplateResponse(request, "tasks.html", {"tasks": tasks})
```

Keep logic in Python and presentation in the template. A template full of `{% if %}` is a
view model waiting to be extracted.

## Exercises

`exercises_16.py`, then `pytest 16_jinja2`. You'll configure an environment properly,
write filters and macros, render an inheritance chain, and prove your autoescaping works.

## Further reading

- [Jinja2 template designer docs](https://jinja.palletsprojects.com/en/stable/templates/)
- [API docs](https://jinja.palletsprojects.com/en/stable/api/)
