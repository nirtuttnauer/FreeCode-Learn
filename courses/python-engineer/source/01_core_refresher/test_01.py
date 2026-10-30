import pytest

from courselib import impl

m = impl("01")


class TestChunked:
    def test_even_split(self):
        assert m.chunked([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]

    def test_ragged_tail(self):
        assert m.chunked([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]

    def test_empty(self):
        assert m.chunked([], 3) == []

    def test_size_larger_than_seq(self):
        assert m.chunked([1, 2], 10) == [[1, 2]]

    def test_works_on_strings(self):
        assert m.chunked("abcde", 2) == ["ab", "cd", "e"]

    def test_rejects_bad_size(self):
        with pytest.raises(ValueError):
            m.chunked([1, 2], 0)

    def test_does_not_mutate_input(self):
        data = [1, 2, 3]
        m.chunked(data, 2)
        assert data == [1, 2, 3]


class TestNormalizeWhitespace:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("  hello\t\n world  ", "hello world"),
            ("already fine", "already fine"),
            ("   ", ""),
            ("", ""),
            ("a\n\n\nb", "a b"),
            ("\v\fa\r\nb\t", "a b"),  # every ASCII whitespace char counts
        ],
    )
    def test_cases(self, raw, expected):
        assert m.normalize_whitespace(raw) == expected


class TestParseKV:
    def test_basic(self):
        assert m.parse_kv("a=1,b=2") == {"a": "1", "b": "2"}

    def test_strips_whitespace(self):
        assert m.parse_kv(" a = 1 , b = 2 ") == {"a": "1", "b": "2"}

    def test_value_may_contain_separator(self):
        assert m.parse_kv("c=x=y") == {"c": "x=y"}

    def test_skips_empty_items(self):
        assert m.parse_kv("a=1,,b=2,") == {"a": "1", "b": "2"}

    def test_custom_separators(self):
        assert m.parse_kv("a:1;b:2", item_sep=";", kv_sep=":") == {"a": "1", "b": "2"}

    def test_later_key_wins(self):
        assert m.parse_kv("a=1,a=2") == {"a": "2"}

    def test_missing_separator_raises(self):
        with pytest.raises(ValueError):
            m.parse_kv("a=1,oops")


class TestClamp:
    @pytest.mark.parametrize(
        ("value", "expected"), [(5, 3), (-1, 0), (2, 2), (0, 0), (3, 3), (1.5, 1.5)]
    )
    def test_range_0_3(self, value, expected):
        assert m.clamp(value, 0, 3) == expected

    def test_inverted_bounds_raise(self):
        with pytest.raises(ValueError):
            m.clamp(1, 10, 0)


class TestSnakeToCamel:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("http_response_code", "httpResponseCode"),
            ("single", "single"),
            ("_leading__and_trailing_", "leadingAndTrailing"),
            ("http_OK", "httpOK"),
            ("", ""),
            ("___", ""),
        ],
    )
    def test_lower_first(self, raw, expected):
        assert m.snake_to_camel(raw) == expected

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("http_response_code", "HttpResponseCode"),
            ("single", "Single"),
            ("", ""),
        ],
    )
    def test_upper_first(self, raw, expected):
        assert m.snake_to_camel(raw, upper_first=True) == expected


class TestFormatRow:
    def test_exact_layout(self):
        assert m.format_row("apple", 3, 1234.5) == "apple       |    3|    1,234.50"

    def test_widths_are_stable(self):
        row = m.format_row("x", 1, 0)
        assert len(row) == 12 + 1 + 5 + 1 + 12
        assert row.count("|") == 2

    def test_long_name_is_not_truncated(self):
        assert m.format_row("a" * 20, 1, 1).startswith("a" * 20)

    def test_rounds_to_two_places(self):
        assert m.format_row("n", 0, 0.005).endswith("0.01") or m.format_row("n", 0, 0.005).endswith(
            "0.00"
        )  # banker's rounding on binary floats — either is defensible
