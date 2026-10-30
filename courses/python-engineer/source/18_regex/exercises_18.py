"""Module 18 exercises.  pytest 18_regex

Compile every pattern once, at module level, with `re.VERBOSE` when it's longer than a
line. And keep the ReDoS section of the README in mind — two of these run on untrusted
input.
"""

from __future__ import annotations

from typing import Any


def parse_log_line(line: str) -> dict[str, str] | None:
    """Parse a log line into a dict, or None when it doesn't match.

    Format:  "2026-08-02 14:31:07 ERROR [app.payments] card declined"
             "2026-08-02T14:31:07 INFO [db] connected"     <- T separator also allowed

    Returns `{"timestamp", "level", "logger", "message"}`.
    - level is one of DEBUG, INFO, WARNING, ERROR, CRITICAL — anything else is no match.
    - the logger name is letters, digits, underscores and dots.
    - the message is the rest of the line, and may be empty.
    - leading/trailing whitespace on the line is tolerated.

    Use named groups and `.groupdict()` — then the function body is two lines.
    """
    raise NotImplementedError


def find_duplicated_words(text: str) -> list[str]:
    """Find words repeated back-to-back ("the the"), case-insensitively.

    >>> find_duplicated_words("This is is a test. The the end.")
    ['is', 'the']

    - Report each duplicate lowercased, in order of first appearance, without repeats.
    - Whitespace between the two words may include newlines.
    - "cat category" is NOT a duplicate — word boundaries matter.

    This needs a BACKREFERENCE (`\\1`) plus a case-insensitive flag.
    """
    raise NotImplementedError


def mask_secrets(text: str) -> str:
    """Redact obvious credentials in a blob of text, preserving structure.

    Rules:
    - `key=value` or `key: value` where the key contains password/passwd/token/secret/
      api_key (case-insensitive) -> the VALUE becomes "***". The key, separator and
      spacing are preserved exactly.
    - Bearer tokens: "Bearer abc123" -> "Bearer ***".
    - Email addresses -> keep the first two characters of the local part, star out the
      rest, keep the domain: "alice@example.com" -> "al***@example.com". A local part of
      1-2 characters is left alone.

    >>> mask_secrets("api_key=abc123 for alice@example.com")
    'api_key=*** for al***@example.com'

    Use `re.sub` with a CALLABLE replacement — the per-match logic is the point.
    """
    raise NotImplementedError


def parse_semver(version: str) -> dict[str, Any] | None:
    """Parse a semantic version, or return None.

    "1.2.3", "1.2.3-alpha.1", "1.2.3+build.5", "1.2.3-rc.1+build.5"

    Returns `{"major": int, "minor": int, "patch": int, "prerelease": str | None,
    "build": str | None}`.

    - Numeric parts have no leading zeros: "01.2.3" is invalid.
    - prerelease and build are dot-separated alphanumerics and hyphens.
    - The WHOLE string must match — this is validation, so use `fullmatch`.
    - Write it with `re.VERBOSE` and a comment per line.
    """
    raise NotImplementedError


def split_sentences(text: str) -> list[str]:
    """Split prose into sentences, keeping the terminating punctuation.

    >>> split_sentences("One. Two!  Three? Four")
    ['One.', 'Two!', 'Three?', 'Four']

    - Split on whitespace that FOLLOWS a `.`, `!` or `?` — a lookbehind, so the
      punctuation stays attached.
    - Don't split on common abbreviations: "Dr.", "Mr.", "Mrs.", "Ms.", "e.g.", "i.e.",
      "vs.", "etc." (a negative lookbehind for those).
    - Strip whitespace from each sentence and drop empty results.
    """
    raise NotImplementedError


def is_redos_safe(pattern: str) -> bool:
    """Crude static check for the nested-quantifier shape that causes ReDoS.

    Return False when the pattern contains a quantified group that itself contains a
    quantifier — `(a+)+`, `(a*)*`, `(a+)*`, `(\\w+\\s*)+`, `(a|aa)+` — and True otherwise.

    A real analyser needs the full NFA; this is the 90% heuristic you'd put in a linter
    to stop the obvious cases reaching production. Document that limitation in your
    docstring — a security check that overstates its guarantees is worse than none.
    """
    raise NotImplementedError
