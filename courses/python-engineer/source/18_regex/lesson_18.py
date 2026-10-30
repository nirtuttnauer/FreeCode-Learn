"""Module 18 — runnable lesson. `python 18_regex/lesson_18.py`"""

from __future__ import annotations

import re
import time

INTRO = r"""A tiny language for describing what text LOOKS like. `\d` is a digit, `+` is "one or
more", so `\d+` finds any number. Watch for the greedy `.*` eating a whole line — and for
the pattern near the end that takes exponentially longer as input grows."""

LOG_LINE = re.compile(
    r"""
    ^(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})   # timestamp
    \s+(?P<level>DEBUG|INFO|WARNING|ERROR|CRITICAL)   # level
    \s+\[(?P<logger>[\w.]+)\]                         # logger name in brackets
    \s+(?P<message>.*)$                               # the rest
    """,
    re.VERBOSE,
)


def the_api() -> None:
    print("\n== search vs match vs fullmatch ==")
    text = "order 12345 shipped"
    print(rf"  search('\d+'):    {re.search(r'\d+', text)}")
    print(rf"  match('\d+'):     {re.match(r'\d+', text)}   <- anchored at the start")
    print(rf"  fullmatch('\d+'): {re.fullmatch(r'\d+', '12345')}   <- use this to validate")

    print("\n== findall vs finditer ==")
    print(rf"  findall:  {re.findall(r'\d+', 'a1 b22 c333')}")
    print("  finditer gives Match objects, lazily — the right choice for large input:")
    for match in re.finditer(r"\d+", "a1 b22"):
        print(f"    {match.group()!r} at {match.span()}")

    print(rf"\n  findall with groups returns TUPLES: {re.findall(r'(\w)(\d)', 'a1 b2')}")


def groups() -> None:
    print("\n== groups ==")
    match = LOG_LINE.match("2026-08-02 14:31:07 ERROR [app.payments] card declined")
    print(f"  groupdict: {match.groupdict()}")
    print(f"  by name:   {match.group('level')}")
    print(f"  span:      {match.span('logger')}")

    print("\n  non-capturing groups keep .groups() clean:")
    print(rf"    with (…):   {re.match(r'(https?)://(\w+)', 'https://example').groups()}")
    print(rf"    with (?:…): {re.match(r'(?:https?)://(\w+)', 'https://example').groups()}")

    print("\n  backreference — find doubled words:")
    print(rf"    {re.findall(r'\b(\w+)\s+\1\b', 'this this is a a test')}")


def greedy_vs_lazy() -> None:
    print("\n== greedy vs non-greedy ==")
    html = "<b>bold</b> and <i>italic</i>"
    print(f"  greedy  <.*>:  {re.findall(r'<.*>', html)}   <- ate everything")
    print(f"  lazy    <.*?>: {re.findall(r'<.*?>', html)}")
    print(f"  better  <[^>]*>: {re.findall(r'<[^>]*>', html)}   <- no backtracking at all")
    print("  (and for real HTML: use a parser, not any of these)")


def lookarounds() -> None:
    print("\n== lookarounds match without consuming ==")
    print(rf"  price after $:      {re.findall(r'(?<=\$)\d+', 'costs $42 not 7')}")
    print(rf"  word NOT followed by !: {re.findall(r'\b\w+\b(?!!)', 'hi! there')}")
    print(rf"  split keeping the delimiter: {re.split(r'(?<=[.!?])\s+', 'One. Two! Three?')}")

    password = "Passw0rd!"
    strong = re.fullmatch(r"(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*\W).{8,}", password)
    print(f"  stacked lookaheads as an AND: {password!r} strong={bool(strong)}")

    print(rf"\n  word boundaries: {re.findall(r'\bcat\b', 'cat concatenate cats cat.')}")


def substitution() -> None:
    print("\n== sub ==")
    text = "contact ada@example.com or bob@corp.io"
    print(rf"  string repl: {re.sub(r'(\w+)@(\w+)', r'\2 AT \1', text)}")
    print(rf"  named repl:  {re.sub(r'(?P<user>\w+)@', r'<\g<user>>@', text)}")

    def redact(match: re.Match) -> str:
        user, domain = match.group(1), match.group(2)
        return user[:2] + "*" * (len(user) - 2) + "@" + domain

    print(rf"  callable repl: {re.sub(r'(\w+)@([\w.]+)', redact, text)}")
    print(f"  subn returns a count: {re.subn(r'@', ' at ', text)[1]} replacements")


def catastrophic_backtracking() -> None:
    print("\n== ReDoS ==")
    evil = re.compile(r"^(a+)+$")
    for n in (18, 20, 22):
        start = time.perf_counter()
        evil.match("a" * n + "b")
        elapsed = time.perf_counter() - start
        print(f"  {n} chars: {elapsed * 1000:>8.1f} ms  <- doubling per character")

    safe = re.compile(r"^a+$")
    start = time.perf_counter()
    safe.match("a" * 10_000 + "b")
    print(f"  rewritten ^a+$ on 10,000 chars: {(time.perf_counter() - start) * 1000:.3f} ms")

    atomic = re.compile(r"^(?>a+)+$")  # 3.11+ atomic group: no backtracking into it
    start = time.perf_counter()
    atomic.match("a" * 30 + "b")
    print(f"  atomic group (?>...) on 30 chars: {(time.perf_counter() - start) * 1000:.3f} ms")
    print("  never run a nested-quantifier pattern on untrusted input")


def when_not_to() -> None:
    print("\n== reach for the right tool ==")
    from urllib.parse import urlparse

    print(f"  urlparse beats any URL regex: {urlparse('https://a.b/c?d=1').netloc}")
    print("  HTML -> html.parser / lxml.  JSON -> json.  CSV -> csv.  TOML -> tomllib.")
    print(f"  and for fixed strings, str is faster: {'error' in 'an error occurred'}")


if __name__ == "__main__":
    print(INTRO)
    the_api()
    groups()
    greedy_vs_lazy()
    lookarounds()
    substitution()
    catastrophic_backtracking()
    when_not_to()
