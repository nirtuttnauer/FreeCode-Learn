"""Acceptance tests for pulse, milestone 1 (the domain).

Run: pytest projects/03_pulse_api -o addopts=""

Note what these tests DON'T need: no database, no client, no fixtures, no async. That is
the payoff of a domain layer that imports nothing.

Milestones 2-6 get their own suites — write them as you go, and make the service tests
parametrised over both repository implementations.
"""

import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "src"))

domain = pytest.importorskip("pulse.domain")
Url, ShortCode, ShortLink = domain.Url, domain.ShortCode, domain.ShortLink

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class TestUrl:
    @pytest.mark.parametrize(
        "raw",
        [
            "https://example.com",
            "http://example.com/path?q=1",
            "https://sub.example.co.uk/a/b#frag",
        ],
    )
    def test_accepts_valid_urls(self, raw):
        assert Url(raw).value

    @pytest.mark.parametrize(
        "raw",
        [
            "javascript:alert(1)",
            "data:text/html,<script>",
            "file:///etc/passwd",
            "ftp://example.com",
            "not a url",
            "",
            "https://",
        ],
    )
    def test_rejects_dangerous_or_malformed(self, raw):
        with pytest.raises(ValueError):
            Url(raw)

    @pytest.mark.parametrize(
        "raw",
        [
            "http://localhost/admin",
            "http://127.0.0.1:8080/",
            "http://10.0.0.5/",
            "http://192.168.1.1/",
            "http://172.16.0.1/",
            "http://169.254.169.254/latest/meta-data/",  # the cloud metadata endpoint
        ],
    )
    def test_rejects_private_addresses(self, raw):
        with pytest.raises(ValueError):
            Url(raw)

    def test_normalises_scheme_and_host(self):
        assert Url("HTTPS://Example.COM/Path").value == "https://example.com/Path"

    def test_strips_default_port(self):
        assert Url("https://example.com:443/x").value == "https://example.com/x"

    def test_length_limit(self):
        with pytest.raises(ValueError):
            Url("https://example.com/" + "a" * 2100)

    def test_is_frozen_and_hashable(self):
        url = Url("https://example.com")
        with pytest.raises(Exception):
            url.value = "other"
        assert len({Url("https://example.com"), Url("https://example.com")}) == 1


class TestShortCode:
    @pytest.mark.parametrize("raw", ["abc123", "aB3xY9z", "a" * 12])
    def test_accepts_valid(self, raw):
        assert str(ShortCode(raw)) == raw

    @pytest.mark.parametrize(
        "raw", ["abc", "a" * 13, "abc-12", "abc 12", "", "abc0de", "abcOde", "abclde", "abcIde"]
    )
    def test_rejects_invalid(self, raw):
        with pytest.raises(ValueError):
            ShortCode(raw)

    def test_excludes_ambiguous_characters(self):
        # 0/O and l/I are the reason support tickets say "it didn't work".
        for ambiguous in "0OlI":
            with pytest.raises(ValueError):
                ShortCode("abcde" + ambiguous)


class TestGenerateCode:
    def test_length_and_alphabet(self):
        code = domain.generate_code(random.Random(1), length=7)
        assert len(str(code)) == 7
        assert all(c in domain.BASE58 for c in str(code))

    def test_is_deterministic_under_a_seed(self):
        a = domain.generate_code(random.Random(42))
        b = domain.generate_code(random.Random(42))
        assert str(a) == str(b)

    def test_different_seeds_differ(self):
        a = domain.generate_code(random.Random(1))
        b = domain.generate_code(random.Random(2))
        assert str(a) != str(b)

    def test_collisions_are_rare(self):
        rng = random.Random(0)
        codes = {str(domain.generate_code(rng)) for _ in range(5000)}
        assert len(codes) == 5000


class TestShortLink:
    def link(self, **overrides):
        defaults = {
            "code": ShortCode("abc123"),
            "target": Url("https://example.com"),
            "owner_id": "owner-1",
            "created_at": NOW,
        }
        return ShortLink(**{**defaults, **overrides})

    def test_defaults(self):
        link = self.link()
        assert link.is_active is True
        assert link.expires_at is None

    def test_never_expires_without_expires_at(self):
        assert self.link().is_expired(NOW + timedelta(days=3650)) is False

    def test_expiry(self):
        link = self.link(expires_at=NOW + timedelta(hours=1))
        assert link.is_expired(NOW) is False
        assert link.is_expired(NOW + timedelta(hours=2)) is True

    def test_naive_datetime_rejected(self):
        with pytest.raises(ValueError):
            self.link(expires_at=NOW + timedelta(hours=1)).is_expired(datetime(2026, 1, 2))

    def test_deactivate_returns_a_new_link(self):
        link = self.link()
        deactivated = link.deactivate()
        assert deactivated.is_active is False
        assert link.is_active is True
        assert deactivated is not link

    def test_frozen(self):
        with pytest.raises(Exception):
            self.link().owner_id = "someone-else"


class TestErrors:
    def test_hierarchy(self):
        for cls in (domain.LinkNotFound, domain.LinkExpired, domain.CodeTaken, domain.QuotaExceeded):
            assert issubclass(cls, domain.PulseError)

    def test_messages_and_payloads(self):
        assert str(domain.LinkNotFound("abc123")) == "link 'abc123' not found"
        assert domain.CodeTaken("abc123").code == "abc123"
        assert domain.QuotaExceeded("owner-1", 100).limit == 100


class TestLayering:
    def test_domain_imports_no_frameworks(self):
        """The architectural rule, as an executable test."""
        source = (Path(__file__).parent / "src/pulse/domain/__init__.py").read_text()
        for banned in ("fastapi", "sqlalchemy", "pydantic", "httpx", "redis"):
            assert banned not in source.lower(), f"domain must not import {banned}"
