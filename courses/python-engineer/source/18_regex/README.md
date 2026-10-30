# 18 — Regular expressions

Regex is the tool you reach for too often and then use at 40% of its power. This module is
the other 60%: named groups, lookarounds, non-greedy matching, `sub` with a callback,
compiled patterns, and knowing when to put the regex down.

## In plain English

A regular expression is a tiny language for describing **what text looks like**, so the
computer can find it. Instead of "find the word cat", you can say "find something that looks
like a date", or "find anything shaped like an email address".

`\d` means a digit. `+` means "one or more of those". So `\d+` finds any run of digits.
That's the whole idea; the rest is vocabulary.

Two things in this module matter more than the syntax:

**Greedy vs lazy.** `.*` means "any characters" and by default it grabs as *much* as
possible. Try to pull HTML tags out of `<b>bold</b> and <i>italic</i>` with `<.*>` and it
matches the **entire line**, because it went as far right as it could. Adding `?` makes it
stop at the first opportunity instead. This trips up everybody.

**The security one.** Some innocent-looking patterns take *exponentially* longer as the
input grows. The lesson has one that takes 5ms on 18 characters, 21ms on 20, and 83ms on 22
— add a few more and it runs until the heat death of the universe. If that pattern runs on
text a stranger typed, they've just taken down your server with a 30-character message.

**Watch out for:** the urge to parse HTML with a regex. Don't. Use an HTML parser. This is
the single most repeated piece of advice in programming for good reason.

## 1. The API

```python
import re

re.search(p, s)      # first match ANYWHERE -> Match | None      <- the one you usually want
re.match(p, s)       # anchored at the START only
re.fullmatch(p, s)   # the whole string must match               <- for validation
re.findall(p, s)     # list of strings (or tuples if there are groups)
re.finditer(p, s)    # lazy iterator of Match objects            <- use on big inputs
re.sub(p, repl, s)   # replace; repl may be a FUNCTION
re.subn(p, repl, s)  # (result, count)
re.split(p, s)       # split on a pattern; captured groups are kept in the output
```

`re.compile(p)` once, at module level, when a pattern is used in a loop — the internal
cache is small and compiled patterns read better with `re.VERBOSE`.

A `Match` gives you `.group(n)`, `.groups()`, `.groupdict()`, `.start()`, `.end()`,
`.span()`, and `.expand()`.

## 2. The syntax that matters

| Pattern | Means |
|---|---|
| `.` | any char except newline (`re.DOTALL` includes it) |
| `\d \w \s` | digit, word char, whitespace (`\D \W \S` negate) |
| `[abc]` `[^abc]` `[a-z]` | character class / negated / range |
| `*` `+` `?` `{2,5}` | greedy repetition |
| `*?` `+?` `??` `{2,5}?` | **non-greedy** — the fix for `<.*>` eating the whole line |
| `^ $` | start/end of string (of each line with `re.MULTILINE`) |
| `\b` | word boundary — `\bcat\b` doesn't match "concatenate" |
| `(...)` | capturing group |
| `(?:...)` | **non-capturing** — group without polluting `.groups()` |
| `(?P<name>...)` | named group -> `.group("name")`, `.groupdict()` |
| `(?P=name)` / `\1` | backreference |
| `A\|B` | alternation (careful: it binds loosely) |
| `(?=...)` `(?!...)` | lookahead: positive / negative |
| `(?<=...)` `(?<!...)` | lookbehind (fixed width only) |
| `(?i)` or `re.I` | flags: `I` ignorecase, `M` multiline, `S` dotall, `X` verbose, `A` ascii |

Lookarounds match **without consuming**, which is how you split on a delimiter you want
to keep, or assert context around a match.

## 3. Readable patterns: `re.VERBOSE`

```python
SEMVER = re.compile(r"""
    ^(?P<major>0|[1-9]\d*)
    \.(?P<minor>0|[1-9]\d*)
    \.(?P<patch>0|[1-9]\d*)
    (?:-(?P<prerelease>[0-9A-Za-z.-]+))?
    (?:\+(?P<build>[0-9A-Za-z.-]+))?$
""", re.VERBOSE)
```

Whitespace and `#` comments are ignored, so a real pattern can be documented in place. Any
regex longer than a line should be written this way.

## 4. `sub` with a function

The most under-used feature in the module:

```python
def redact(match: re.Match) -> str:
    return match.group(1) + "*" * len(match.group(2))

re.sub(r"(\w{2})(\w+@\w+\.\w+)", redact, text)
```

The replacement string form supports `\1` and `\g<name>`; the callable form lets you run
arbitrary logic per match, which beats a loop of `str.replace` every time.

## 5. Catastrophic backtracking — the security bit

```python
re.match(r"^(a+)+$", "a" * 30 + "b")     # exponential. This hangs.
```

Nested quantifiers over overlapping alternatives can take exponential time. If the pattern
runs on **user input**, that's a denial-of-service (ReDoS).

Defences:
- Avoid nested quantifiers `(x+)+`, `(x*)*`, and alternations that can match the same text.
- Anchor patterns and prefer explicit character classes over `.*`.
- Make repetition possessive-ish by restructuring (Python has no atomic groups until
  3.11's `(?>...)` — which it *does* have now, so use it).
- Cap input length before matching.
- For untrusted patterns, use the `regex` package with a timeout, or don't accept them.

## 6. When NOT to use regex

- **HTML/XML** → an HTML parser. Non-negotiable.
- **JSON/YAML/TOML/CSV** → the parsers in the stdlib (module 19).
- **URLs** → `urllib.parse`. **Emails** → the real grammar is monstrous; validate loosely
  and send a confirmation link.
- **Fixed strings** → `str.startswith`, `in`, `split`, `partition`. They're faster and
  clearer.
- Structured logs → log JSON in the first place, then you never parse them at all.

## Exercises

`exercises_18.py`, then `pytest 18_regex`.

## Further reading

- [`re` docs](https://docs.python.org/3/library/re.html) and the [Regex HOWTO](https://docs.python.org/3/howto/regex.html)
- [regex101.com](https://regex101.com) — set it to Python and use the explain pane
