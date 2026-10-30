from dataclasses import dataclass

import pytest
from jinja2 import StrictUndefined, UndefinedError
from jinja2.exceptions import SecurityError

from courselib import impl

m = impl("16")


@dataclass
class Item:
    name: str


@dataclass
class Task:
    days_left: int


class TestEnvironment:
    @pytest.fixture
    def env(self):
        return m.build_environment({"greet.html": "hi {{ name }}"})

    def test_loader_is_wired(self, env):
        assert env.get_template("greet.html").render(name="ada") == "hi ada"

    def test_autoescape_on_for_html(self, env):
        assert env.get_template("greet.html").render(name="<b>") == "hi &lt;b&gt;"

    def test_strict_undefined(self, env):
        assert env.undefined is StrictUndefined
        with pytest.raises(UndefinedError):
            env.get_template("greet.html").render()

    def test_trim_and_lstrip(self, env):
        assert env.trim_blocks and env.lstrip_blocks

    def test_currency_filter(self, env):
        assert env.filters["currency"](1234.5) == "$1,234.50"
        assert env.filters["currency"](0) == "$0.00"

    def test_pluralise_filter(self, env):
        p = env.filters["pluralise"]
        assert p(1, "file") == "1 file"
        assert p(2, "file") == "2 files"
        assert p(0, "file") == "0 files"
        assert p(2, "box", "boxes") == "2 boxes"

    def test_overdue_test(self, env):
        assert env.tests["overdue"](Task(-1)) is True
        assert env.tests["overdue"](Task(3)) is False

    def test_site_name_global(self, env):
        assert env.globals["site_name"] == "Python Engineer"


class TestRenderString:
    def test_basic(self):
        assert m.render_string("{{ a }}+{{ b }}", a=1, b=2) == "1+2"

    def test_filters_available(self):
        assert m.render_string("{{ v | currency }}", v=5) == "$5.00"

    def test_globals_available(self):
        assert m.render_string("{{ site_name }}") == "Python Engineer"

    def test_strict(self):
        with pytest.raises(UndefinedError):
            m.render_string("{{ missing }}")

    def test_custom_test_available(self):
        out = m.render_string("{% if t is overdue %}late{% endif %}", t=Task(-2))
        assert out == "late"


class TestInvoice:
    @pytest.fixture
    def env(self):
        return m.build_environment({})

    def test_single_line(self, env):
        got = m.render_invoice(env, "ACME", [{"name": "Widget", "quantity": 2, "unit_price": 9.5}])
        assert got == (
            "INVOICE for ACME\n"
            "================\n"
            "Widget x2 @ $9.50 = $19.00\n"
            "----------------\n"
            "TOTAL: $19.00\n"
            "1 line"
        )

    def test_multiple_lines_and_total(self, env):
        lines = [
            {"name": "A", "quantity": 1, "unit_price": 10},
            {"name": "B", "quantity": 3, "unit_price": 2.5},
        ]
        got = m.render_invoice(env, "Co", lines)
        assert "A x1 @ $10.00 = $10.00" in got
        assert "B x3 @ $2.50 = $7.50" in got
        assert "TOTAL: $17.50" in got
        assert got.endswith("2 lines")

    def test_empty(self, env):
        got = m.render_invoice(env, "Nobody", [])
        assert "(no items)" in got
        assert "TOTAL: $0.00" in got
        assert got.endswith("0 lines")

    def test_no_trailing_newline(self, env):
        assert not m.render_invoice(env, "X", []).endswith("\n")

    def test_rule_widths(self, env):
        lines = m.render_invoice(env, "X", []).splitlines()
        assert lines[1] == "=" * 16
        assert "-" * 16 in lines

    def test_large_numbers_are_grouped(self, env):
        got = m.render_invoice(env, "X", [{"name": "N", "quantity": 1000, "unit_price": 12.5}])
        assert "TOTAL: $12,500.00" in got


class TestPage:
    def test_heading_in_h1(self):
        assert "<h1>Inventory</h1>" in m.render_page("Inventory", [])

    def test_items_rendered(self):
        html = m.render_page("Stock", [Item("keyboard"), Item("monitor")])
        assert "<li>keyboard</li>" in html
        assert "<li>monitor</li>" in html

    def test_empty_branch(self):
        assert "<li>empty</li>" in m.render_page("Stock", [])

    def test_title_uses_super_and_the_global(self):
        html = m.render_page("Stock", [])
        assert "<title>Stock · Python Engineer</title>" in html

    def test_inheritance_produced_a_full_document(self):
        html = m.render_page("Stock", [])
        assert html.strip().startswith("<html>")
        assert "</html>" in html

    def test_hostile_item_names_are_escaped(self):
        html = m.render_page("Stock", [Item("<script>steal()</script>")])
        assert "<script>steal()" not in html
        assert "&lt;script&gt;" in html

    def test_hostile_heading_is_escaped(self):
        assert "<img src=x" not in m.render_page("<img src=x onerror=1>", [])


class TestBadge:
    def test_default_kind(self):
        assert m.render_badge("new") == '<span class="badge badge-info">new</span>'

    def test_custom_kind(self):
        assert m.render_badge("late", "danger") == '<span class="badge badge-danger">late</span>'

    def test_escapes_text(self):
        assert "<b>" not in m.render_badge("<b>bold</b>")


class TestSandbox:
    def test_renders_normal_templates(self):
        assert m.render_untrusted("hello {{ name }}", name="ada") == "hello ada"

    def test_escapes_output(self):
        assert m.render_untrusted("{{ v }}", v="<b>") == "&lt;b&gt;"

    @pytest.mark.parametrize(
        "attack",
        [
            "{{ ''.__class__ }}",
            "{{ ''.__class__.__mro__ }}",
            "{{ [].__class__.__base__.__subclasses__() }}",
            "{{ config.__class__.__init__.__globals__ }}",
        ],
    )
    def test_blocks_escapes(self, attack):
        with pytest.raises(SecurityError):
            m.render_untrusted(attack, config={})

    def test_a_normal_environment_would_have_leaked(self):
        # Contrast: proving the sandbox is doing something.
        leaked = m.render_string("{{ ''.__class__.__name__ }}")
        assert leaked == "str"
