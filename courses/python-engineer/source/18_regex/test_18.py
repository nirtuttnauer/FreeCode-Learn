import pytest

from courselib import impl

m = impl("18")


class TestParseLogLine:
    def test_basic(self):
        got = m.parse_log_line("2026-08-02 14:31:07 ERROR [app.payments] card declined")
        assert got == {
            "timestamp": "2026-08-02 14:31:07",
            "level": "ERROR",
            "logger": "app.payments",
            "message": "card declined",
        }

    def test_t_separator(self):
        assert m.parse_log_line("2026-08-02T14:31:07 INFO [db] connected")["level"] == "INFO"

    def test_empty_message(self):
        assert m.parse_log_line("2026-08-02 00:00:00 INFO [x] ")["message"] == ""

    def test_surrounding_whitespace(self):
        assert m.parse_log_line("  2026-08-02 00:00:00 INFO [x] hi  ")["message"] == "hi"

    @pytest.mark.parametrize(
        "line",
        [
            "not a log line",
            "2026-08-02 14:31:07 TRACE [x] unknown level",
            "2026-08-02 ERROR [x] no time",
            "",
        ],
    )
    def test_non_matching(self, line):
        assert m.parse_log_line(line) is None

    def test_message_may_contain_brackets(self):
        got = m.parse_log_line("2026-08-02 00:00:00 INFO [x] got [1, 2] back")
        assert got["message"] == "got [1, 2] back"


class TestFindDuplicatedWords:
    def test_basic(self):
        assert m.find_duplicated_words("This is is a test. The the end.") == ["is", "the"]

    def test_case_insensitive(self):
        assert m.find_duplicated_words("The THE end") == ["the"]

    def test_no_duplicates(self):
        assert m.find_duplicated_words("all unique words here") == []

    def test_prefix_is_not_a_duplicate(self):
        assert m.find_duplicated_words("cat category") == []

    def test_across_newlines(self):
        assert m.find_duplicated_words("word\nword") == ["word"]

    def test_reports_each_word_once(self):
        assert m.find_duplicated_words("a a and a a") == ["a"]


class TestMaskSecrets:
    def test_key_value(self):
        assert m.mask_secrets("api_key=abc123") == "api_key=***"

    def test_colon_separator_and_spacing_preserved(self):
        assert m.mask_secrets("password: hunter2") == "password: ***"

    @pytest.mark.parametrize("key", ["PASSWORD", "db_passwd", "auth_token", "client_secret"])
    def test_key_variants(self, key):
        assert m.mask_secrets(f"{key}=value") == f"{key}=***"

    def test_bearer_token(self):
        assert m.mask_secrets("Authorization: Bearer eyJhbGc") == "Authorization: Bearer ***"

    def test_email(self):
        assert m.mask_secrets("alice@example.com") == "al***@example.com"

    def test_short_local_part_untouched(self):
        assert m.mask_secrets("ab@example.com") == "ab@example.com"

    def test_combined(self):
        assert m.mask_secrets("api_key=abc123 for alice@example.com") == (
            "api_key=*** for al***@example.com"
        )

    def test_innocent_text_untouched(self):
        assert m.mask_secrets("username=alice port=5432") == "username=alice port=5432"


class TestParseSemver:
    def test_basic(self):
        assert m.parse_semver("1.2.3") == {
            "major": 1,
            "minor": 2,
            "patch": 3,
            "prerelease": None,
            "build": None,
        }

    def test_prerelease(self):
        assert m.parse_semver("1.2.3-alpha.1")["prerelease"] == "alpha.1"

    def test_build(self):
        assert m.parse_semver("1.2.3+build.5")["build"] == "build.5"

    def test_both(self):
        got = m.parse_semver("1.2.3-rc.1+build.5")
        assert (got["prerelease"], got["build"]) == ("rc.1", "build.5")

    def test_parts_are_ints(self):
        assert all(isinstance(m.parse_semver("10.20.30")[k], int) for k in ["major", "minor", "patch"])

    def test_zero_is_allowed(self):
        assert m.parse_semver("0.0.0")["major"] == 0

    @pytest.mark.parametrize(
        "bad", ["1.2", "01.2.3", "1.02.3", "v1.2.3", "1.2.3.4", "", "1.2.3-", "a.b.c", " 1.2.3"]
    )
    def test_invalid(self, bad):
        assert m.parse_semver(bad) is None

    def test_must_match_the_whole_string(self):
        assert m.parse_semver("1.2.3 and more") is None


class TestSplitSentences:
    def test_basic(self):
        assert m.split_sentences("One. Two!  Three? Four") == ["One.", "Two!", "Three?", "Four"]

    def test_single_sentence(self):
        assert m.split_sentences("Just one.") == ["Just one."]

    def test_empty(self):
        assert m.split_sentences("") == []
        assert m.split_sentences("   ") == []

    @pytest.mark.parametrize(
        "text",
        [
            "Dr. Smith arrived.",
            "Mr. and Mrs. Jones left.",
            "Use e.g. this one.",
            "Python vs. Java.",
        ],
    )
    def test_abbreviations_do_not_split(self, text):
        assert len(m.split_sentences(text)) == 1

    def test_newlines_count_as_whitespace(self):
        assert m.split_sentences("One.\nTwo.") == ["One.", "Two."]


class TestIsRedosSafe:
    @pytest.mark.parametrize("pattern", [r"^(a+)+$", r"(a*)*", r"(a+)*", r"(\w+\s*)+", r"(a|aa)+"])
    def test_flags_nested_quantifiers(self, pattern):
        assert m.is_redos_safe(pattern) is False

    @pytest.mark.parametrize("pattern", [r"^a+$", r"\d{4}-\d{2}", r"(?:abc)+", r"[^>]*", r"\w+@\w+"])
    def test_allows_safe_patterns(self, pattern):
        assert m.is_redos_safe(pattern) is True

    def test_empty_pattern(self):
        assert m.is_redos_safe("") is True
