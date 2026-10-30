import json

import pytest

from courselib import impl

m = impl("25")

FAST = 2**12  # keep scrypt cheap in tests; production uses 2**14+


class TestHashPassword:
    def test_format(self):
        parts = m.hash_password("hunter2", n=FAST).split("$")
        assert parts[0] == "scrypt"
        assert parts[1] == str(FAST)
        assert len(parts) == 6

    def test_salt_is_random(self):
        assert m.hash_password("same", n=FAST) != m.hash_password("same", n=FAST)

    def test_plaintext_is_not_present(self):
        assert "hunter2" not in m.hash_password("hunter2", n=FAST)

    def test_empty_password_rejected(self):
        with pytest.raises(ValueError):
            m.hash_password("", n=FAST)

    def test_unicode_passwords(self):
        stored = m.hash_password("pässwörd🔐", n=FAST)
        assert m.verify_password(stored, "pässwörd🔐")


class TestVerifyPassword:
    def test_correct_password(self):
        assert m.verify_password(m.hash_password("hunter2", n=FAST), "hunter2")

    def test_wrong_password(self):
        assert not m.verify_password(m.hash_password("hunter2", n=FAST), "hunter3")

    def test_case_sensitive(self):
        assert not m.verify_password(m.hash_password("Hunter2", n=FAST), "hunter2")

    def test_uses_the_stored_parameters(self):
        # Hashed with one cost, verified without being told — the params must be parsed out.
        assert m.verify_password(m.hash_password("x", n=2**13), "x")

    @pytest.mark.parametrize(
        "stored",
        ["", "garbage", "scrypt$notanint$8$1$aa$bb", "md5$1$1$1$aa$bb", "scrypt$16384$8$1$zz$yy", "$$$$$"],
    )
    def test_malformed_records_return_false_and_never_raise(self, stored):
        assert m.verify_password(stored, "anything") is False

    def test_empty_password_against_a_valid_hash(self):
        assert not m.verify_password(m.hash_password("real", n=FAST), "")


class TestGenerateToken:
    def test_returns_a_string(self):
        assert isinstance(m.generate_token(), str)

    def test_long_enough(self):
        assert len(m.generate_token(32)) >= 32

    def test_url_safe(self):
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
        assert set(m.generate_token(32)) <= allowed

    def test_unique(self):
        assert len({m.generate_token(16) for _ in range(10_000)}) == 10_000

    def test_rejects_short_tokens(self):
        with pytest.raises(ValueError):
            m.generate_token(8)


SECRET = b"shared-signing-key"
BODY = b'{"event":"payment.succeeded"}'
NOW = 1_800_000_000


class TestSignatures:
    def test_deterministic(self):
        assert m.sign_payload(SECRET, BODY, NOW) == m.sign_payload(SECRET, BODY, NOW)

    def test_hex_sha256(self):
        signature = m.sign_payload(SECRET, BODY, NOW)
        assert len(signature) == 64
        int(signature, 16)

    def test_timestamp_is_part_of_the_signature(self):
        assert m.sign_payload(SECRET, BODY, NOW) != m.sign_payload(SECRET, BODY, NOW + 1)

    def test_body_is_part_of_the_signature(self):
        assert m.sign_payload(SECRET, BODY, NOW) != m.sign_payload(SECRET, BODY + b" ", NOW)

    def test_secret_matters(self):
        assert m.sign_payload(SECRET, BODY, NOW) != m.sign_payload(b"other", BODY, NOW)

    def test_valid_signature_verifies(self):
        signature = m.sign_payload(SECRET, BODY, NOW)
        assert m.verify_payload(SECRET, BODY, NOW, signature, now=NOW)

    def test_tampered_body_rejected(self):
        signature = m.sign_payload(SECRET, BODY, NOW)
        assert not m.verify_payload(SECRET, BODY + b"x", NOW, signature, now=NOW)

    def test_wrong_secret_rejected(self):
        signature = m.sign_payload(SECRET, BODY, NOW)
        assert not m.verify_payload(b"wrong", BODY, NOW, signature, now=NOW)

    def test_replay_outside_the_window_rejected(self):
        signature = m.sign_payload(SECRET, BODY, NOW)
        assert not m.verify_payload(SECRET, BODY, NOW, signature, now=NOW + 3600)

    def test_inside_the_window_accepted(self):
        signature = m.sign_payload(SECRET, BODY, NOW)
        assert m.verify_payload(SECRET, BODY, NOW, signature, now=NOW + 60)

    def test_future_timestamp_rejected(self):
        signature = m.sign_payload(SECRET, BODY, NOW + 3600)
        assert not m.verify_payload(SECRET, BODY, NOW + 3600, signature, now=NOW)

    @pytest.mark.parametrize("signature", ["", "zzz", "0" * 64, None])
    def test_malformed_signatures_return_false(self, signature):
        assert m.verify_payload(SECRET, BODY, NOW, signature, now=NOW) is False

    def test_a_fresh_timestamp_but_stale_signature_is_rejected(self):
        old = m.sign_payload(SECRET, BODY, NOW - 10)
        assert not m.verify_payload(SECRET, BODY, NOW, old, now=NOW)


class TestSanitizeFilename:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("report.pdf", "report.pdf"),
            ("../../etc/passwd", "passwd"),
            ("/etc/shadow", "shadow"),
            ("C:\\windows\\system32\\cmd.exe", "cmd.exe"),
            ("my file (final).txt", "my_file__final_.txt"),
            ("..", "unnamed"),
            ("...", "unnamed"),
            ("", "unnamed"),
            (".hidden", "hidden"),
        ],
    )
    def test_cases(self, raw, expected):
        assert m.sanitize_filename(raw) == expected

    def test_no_separators_survive(self):
        for raw in ["a/b/c.txt", "a\\b\\c.txt", "../../../x"]:
            assert "/" not in m.sanitize_filename(raw)
            assert "\\" not in m.sanitize_filename(raw)

    def test_no_double_dots_survive(self):
        assert ".." not in m.sanitize_filename("a..b..c")

    def test_null_bytes_and_control_chars(self):
        assert "\x00" not in m.sanitize_filename("evil\x00.txt")

    def test_truncation_keeps_the_extension(self):
        got = m.sanitize_filename("a" * 300 + ".txt", max_length=50)
        assert len(got) <= 50
        assert got.endswith(".txt")

    def test_windows_reserved_names(self):
        for reserved in ["CON", "con.txt", "PRN", "aux", "COM1", "lpt9.log"]:
            assert m.sanitize_filename(reserved).startswith("_")

    def test_normal_names_are_not_prefixed(self):
        assert not m.sanitize_filename("console.log").startswith("_")

    def test_unicode_is_replaced_not_dropped(self):
        assert m.sanitize_filename("файл.txt").endswith(".txt")


class TestIsSafeUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "https://api.example.com/v1",
            "http://example.com",
            "https://sub.domain.example.com/path?q=1",
            "https://93.184.216.34/",
        ],
    )
    def test_allows_public_urls(self, url):
        assert m.is_safe_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "javascript:alert(1)",
            "data:text/html,<script>",
            "file:///etc/passwd",
            "ftp://example.com",
            "not a url",
            "",
            "http://",
        ],
    )
    def test_rejects_bad_schemes(self, url):
        assert m.is_safe_url(url) is False

    @pytest.mark.parametrize(
        "url",
        [
            "http://localhost/admin",
            "http://127.0.0.1:8080/",
            "http://0.0.0.0/",
            "http://10.0.0.5/",
            "http://192.168.1.1/",
            "http://172.16.0.1/",
            "http://169.254.169.254/latest/meta-data/",
            "http://app.localhost/",
            "http://db.internal/",
            "http://printer.local/",
        ],
    )
    def test_rejects_internal_targets(self, url):
        assert m.is_safe_url(url) is False

    def test_rejects_embedded_credentials(self):
        assert m.is_safe_url("https://user:pass@evil.com/") is False

    def test_rejects_header_injection(self):
        assert m.is_safe_url("https://example.com/\r\nX-Injected: 1") is False

    def test_allow_list(self):
        allowed = frozenset({"api.example.com"})
        assert m.is_safe_url("https://api.example.com/x", allowed) is True
        assert m.is_safe_url("https://evil.com/x", allowed) is False

    def test_allow_list_is_case_insensitive(self):
        assert m.is_safe_url("https://API.Example.com/x", frozenset({"api.example.com"})) is True

    def test_allow_list_matches_exactly_not_by_suffix(self):
        # "evil-api.example.com.attacker.com" must not pass an "api.example.com" list.
        assert m.is_safe_url("https://api.example.com.attacker.com/", frozenset({"api.example.com"})) is False


class TestRedact:
    def test_redacts_obvious_keys(self):
        got = m.redact({"password": "hunter2", "user": "ada"})
        assert got == {"password": "[REDACTED]", "user": "ada"}

    @pytest.mark.parametrize(
        "key",
        ["password", "PASSWORD", "db_passwd", "api_key", "apiKey", "authorization",
         "session_id", "access_token", "private_key", "Cookie", "credentials"],
    )
    def test_key_variants(self, key):
        assert m.redact({key: "x"})[key] == "[REDACTED]"

    def test_nested_dicts(self):
        got = m.redact({"db": {"host": "x", "password": "secret"}})
        assert got["db"]["password"] == "[REDACTED]"
        assert got["db"]["host"] == "x"

    def test_lists_and_tuples(self):
        got = m.redact({"users": [{"token": "a"}, {"token": "b"}]})
        assert [u["token"] for u in got["users"]] == ["[REDACTED]", "[REDACTED]"]
        assert isinstance(m.redact(({"token": "a"},))[0], dict)
        assert isinstance(m.redact(({"token": "a"},)), tuple)

    def test_non_string_secret_values(self):
        assert m.redact({"token": 12345})["token"] == "[REDACTED]"
        assert m.redact({"secret": None})["secret"] == "[REDACTED]"

    def test_extra_keys(self):
        got = m.redact({"ssn": "123"}, extra_keys=frozenset({"ssn"}))
        assert got["ssn"] == "[REDACTED]"

    def test_input_is_not_modified(self):
        original = {"password": "hunter2", "nested": {"token": "abc"}}
        m.redact(original)
        assert original["password"] == "hunter2"
        assert original["nested"]["token"] == "abc"

    def test_scalars_pass_through(self):
        assert m.redact("plain") == "plain"
        assert m.redact(42) == 42

    def test_circular_structures_do_not_recurse_forever(self):
        data = {"name": "loop"}
        data["self"] = data
        got = m.redact(data)
        assert got["name"] == "loop"


class TestParseJsonSafely:
    def test_valid_json(self):
        assert m.parse_json_safely('{"a": 1}') == {"a": 1}

    def test_arrays_and_scalars(self):
        assert m.parse_json_safely("[1, 2, 3]") == [1, 2, 3]
        assert m.parse_json_safely('"hello"') == "hello"

    def test_invalid_json_raises_valueerror(self):
        with pytest.raises(ValueError):
            m.parse_json_safely("{not json")

    def test_json_decode_error_is_wrapped(self):
        try:
            m.parse_json_safely("{bad")
        except Exception as exc:
            assert not isinstance(exc, json.JSONDecodeError) or isinstance(exc, ValueError)

    def test_size_limit(self):
        with pytest.raises(ValueError, match="bytes"):
            m.parse_json_safely(json.dumps(["x" * 100] * 200), max_bytes=1000)

    def test_size_limit_counts_utf8_bytes(self):
        payload = json.dumps("é" * 400)  # 2 bytes each
        with pytest.raises(ValueError):
            m.parse_json_safely(payload, max_bytes=500)

    def test_depth_limit(self):
        deep = json.dumps({"a": 1})
        for _ in range(50):
            deep = json.dumps({"n": json.loads(deep)})
        with pytest.raises(ValueError, match="nest"):
            m.parse_json_safely(deep, max_depth=10)

    def test_depth_within_the_limit_is_fine(self):
        nested = {"a": {"b": {"c": 1}}}
        assert m.parse_json_safely(json.dumps(nested), max_depth=10) == nested

    def test_wide_but_shallow_is_allowed(self):
        assert len(m.parse_json_safely(json.dumps(list(range(1000))), max_depth=3)) == 1000

    def test_deep_arrays_count_too(self):
        deep = json.dumps(json.loads("[" * 60 + "]" * 60))
        with pytest.raises(ValueError):
            m.parse_json_safely(deep, max_depth=10)

    def test_extremely_deep_input_does_not_crash_the_process(self):
        # 5000 deep: json.loads itself may hit RecursionError — it must surface as ValueError.
        hostile = "[" * 5000 + "]" * 5000
        with pytest.raises(ValueError):
            m.parse_json_safely(hostile, max_depth=20)
