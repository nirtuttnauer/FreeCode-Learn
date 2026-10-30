"""Module 18 — reference solutions."""

from __future__ import annotations

import re
from typing import Any

LOG_LINE = re.compile(
    r"""
    ^\s*
    (?P<timestamp>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})
    \s+(?P<level>DEBUG|INFO|WARNING|ERROR|CRITICAL)
    \s+\[(?P<logger>[\w.]+)\]
    \s*(?P<message>.*?)\s*$
    """,
    re.VERBOSE,
)

DUPLICATE_WORD = re.compile(r"\b(\w+)\s+\1\b", re.IGNORECASE)

SECRET_ASSIGNMENT = re.compile(
    r"""
    (?P<key>\w*(?:password|passwd|token|secret|api_key)\w*)   # a credential-ish key
    (?P<sep>\s*[=:]\s*)                                       # separator, spacing kept
    (?P<value>\S+)
    """,
    re.VERBOSE | re.IGNORECASE,
)
BEARER = re.compile(r"\bBearer\s+\S+", re.IGNORECASE)
EMAIL = re.compile(r"\b(?P<local>[\w.+-]+)@(?P<domain>[\w-]+\.[\w.-]+)\b")

SEMVER = re.compile(
    r"""
    ^(?P<major>0|[1-9]\d*)                          # no leading zeros
    \.(?P<minor>0|[1-9]\d*)
    \.(?P<patch>0|[1-9]\d*)
    (?:-(?P<prerelease>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?
    (?:\+(?P<build>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$
    """,
    re.VERBOSE,
)

# Each lookbehind must be fixed-width, so they're written as a chain rather than one
# alternation. Read it as: "split on whitespace after . ! or ?, unless what precedes it
# is one of these abbreviations".
SENTENCE_BREAK = re.compile(
    r"""
    (?<=[.!?])
    (?<!\bDr\.)(?<!\bMr\.)(?<!\bMrs\.)(?<!\bMs\.)
    (?<!\bvs\.)(?<!\betc\.)(?<!\be\.g\.)(?<!\bi\.e\.)
    \s+
    """,
    re.VERBOSE,
)

# A quantified group whose body itself contains a quantifier or an alternation.
NESTED_QUANTIFIER = re.compile(r"\([^()]*(?:[*+]|\{\d+,\d*\}|\|)[^()]*\)\s*(?:[*+]|\{\d+,\d*\})")


def parse_log_line(line: str) -> dict[str, str] | None:
    match = LOG_LINE.match(line)
    return match.groupdict() if match else None


def find_duplicated_words(text: str) -> list[str]:
    seen: list[str] = []
    for match in DUPLICATE_WORD.finditer(text):
        word = match.group(1).lower()
        if word not in seen:
            seen.append(word)
    return seen


def mask_secrets(text: str) -> str:
    def mask_assignment(match: re.Match[str]) -> str:
        return f"{match.group('key')}{match.group('sep')}***"

    def mask_email(match: re.Match[str]) -> str:
        local = match.group("local")
        if len(local) <= 2:
            return match.group(0)
        return f"{local[:2]}***@{match.group('domain')}"

    text = SECRET_ASSIGNMENT.sub(mask_assignment, text)
    text = BEARER.sub("Bearer ***", text)
    return EMAIL.sub(mask_email, text)


def parse_semver(version: str) -> dict[str, Any] | None:
    match = SEMVER.fullmatch(version)
    if match is None:
        return None
    parts = match.groupdict()
    return {
        "major": int(parts["major"]),
        "minor": int(parts["minor"]),
        "patch": int(parts["patch"]),
        "prerelease": parts["prerelease"],
        "build": parts["build"],
    }


def split_sentences(text: str) -> list[str]:
    return [chunk.strip() for chunk in SENTENCE_BREAK.split(text) if chunk.strip()]


def is_redos_safe(pattern: str) -> bool:
    """Heuristic only: catches the obvious nested-quantifier shapes, not every ReDoS."""
    return NESTED_QUANTIFIER.search(pattern) is None
