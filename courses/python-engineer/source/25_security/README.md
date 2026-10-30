# 25 — Security for Python developers

Defensive security: how the code *you* write gets broken, and what to write instead. Every
item here is a Python-specific mechanism, not general theory — the injection sinks are
Python functions, the crypto is `hashlib`/`hmac`/`secrets`, and the supply chain is pip.

The governing idea: **untrusted input reaches a dangerous function**. Security work is
finding those pairs and putting something between them.

## In plain English

Almost every security bug in your own code is the same shape:

> **Something a stranger typed reached something dangerous.**

That's it. A username reached the database command. A filename reached the filesystem. A URL
reached your HTTP client. A template reached the template engine. Once you're looking for
that shape, security stops being a mystical specialism and becomes a checklist.

So the job is to find those pairs and put something in between. This module is that
something, function by function.

A few things that surprise people:

- **Loading a pickle file runs code.** Not "could be exploited" — the format is *designed*
  to reconstruct objects, and reconstructing can mean "run this". If a stranger can supply
  the file, they can run anything. The lesson demonstrates it in five lines.
- **`random` is predictable.** It's built for simulations, not secrecy. Watch enough of its
  output and you can compute every future value. Use it for a password-reset link and you've
  handed out account takeovers. Use `secrets` instead.
- **Password hashing wants to be SLOW.** That sounds backwards until you realise the attacker
  is trying billions of guesses per second on a stolen database. `sha256` is fast, therefore
  terrible for this. `scrypt` is deliberately ~1500× slower — measured in the lesson.

**Watch out for:** none of this is about being clever. It's about knowing the short list of
dangerous functions and never letting untrusted input reach one unescorted.

## 1. Injection — the dangerous functions, by name

| Sink | Attack | Defence |
|---|---|---|
| `cursor.execute(f"... {x}")` | SQL injection | **parameters** (module 20) |
| `subprocess.run(cmd, shell=True)` | command injection | a **list** of args, no shell |
| `os.system`, `os.popen` | command injection | `subprocess.run([...])` |
| `eval`, `exec`, `compile` | arbitrary code | don't. `ast.literal_eval` for literals |
| `pickle.loads`, `shelve`, `dill` | **arbitrary code on load** | JSON; sign the blob if you must |
| `yaml.load` | arbitrary code | `yaml.safe_load` |
| `Environment().from_string(user_input)` | SSTI → RCE | `SandboxedEnvironment` (module 16) |
| `open(user_path)` | path traversal | resolve + `is_relative_to` (module 19) |
| `httpx.get(user_url)` | SSRF | allow-list the host, block private ranges |
| `re.match(user_pattern, s)` | ReDoS | don't accept patterns; bound input (module 18) |
| `logging` a user string | log injection / secret leak | structured fields + redaction |

`pickle` deserves emphasis: **loading a pickle is executing code.** A `__reduce__` method
in the payload runs whatever it likes. "It's only from our own cache/queue/S3 bucket" is
exactly the trust boundary attackers cross.

```python
ast.literal_eval("{'a': 1}")     # safe: literals only, no calls, no attribute access
```

## 2. Passwords

```python
import hashlib, secrets

salt = secrets.token_bytes(16)                     # per user, stored alongside
key = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
```

- **Never** `sha256(password)`. Fast hashes are the point of GPU cracking rigs — billions
  of guesses per second.
- Use a **slow, salted, memory-hard KDF**: `argon2` (`argon2-cffi`, best), `bcrypt`, or
  stdlib `hashlib.scrypt`/`pbkdf2_hmac` when you can't add a dependency.
- Unique random salt per user. Store the parameters with the hash so you can raise the
  cost later.
- Compare with `secrets.compare_digest`, never `==`.
- Never log, echo, or put a password in a URL.

## 3. Randomness

```python
import random, secrets

random.random()          # a Mersenne Twister PRNG: PREDICTABLE. Simulations and tests only.
secrets.token_urlsafe(32)   # CSPRNG: tokens, session ids, password resets, API keys
secrets.token_bytes(16)
secrets.choice(alphabet)
```

Observing ~624 outputs of `random` is enough to reconstruct its state and predict every
future value. Using it for a password-reset token is a full account-takeover bug.

## 4. Timing attacks

```python
if provided_token == stored_token:      # leaks the length of the matching prefix
if secrets.compare_digest(provided_token, stored_token):   # constant time
```

`==` on `bytes`/`str` short-circuits at the first differing byte, so its cost depends on
how long a prefix matched. The lesson file measures this: at 1 MB the difference between
"differs at byte 0" and "differs at the last byte" is ~1400×.

Be honest about the threat model, though. At a realistic 32-byte token the difference is a
couple of nanoseconds, buried in noise — a *remote* timing attack on a short token needs
enormous sampling and is not the easy win it's often presented as. The reason to use
`compare_digest` anyway is that it is **free**: constant time regardless of input, no
measurable cost, and you don't control the conditions an attacker gets (local process,
shared tenancy, a much longer secret). Make it the habit for every secret comparison —
tokens, HMACs, API keys — and stop thinking about it.

## 5. Signing and verifying (webhooks)

```python
import hmac, hashlib

expected = hmac.new(secret, f"{timestamp}.{body}".encode(), hashlib.sha256).hexdigest()
if not hmac.compare_digest(expected, header_signature):
    raise Unauthorized
if abs(time.time() - timestamp) > 300:          # reject replays
    raise Unauthorized
```

Sign the **timestamp and the raw body** together, and verify before parsing. Without the
timestamp, a captured request can be replayed forever.

## 6. TLS and outbound requests

- Never `verify=False` (httpx/requests) or `ssl._create_unverified_context()`. That's
  opting into a man-in-the-middle.
- Pin a private CA with `verify="/path/ca.pem"` if you need one.
- **SSRF**: if a user supplies a URL you fetch, allow-list the scheme and host, and block
  `localhost`, `127.0.0.0/8`, `10/8`, `172.16/12`, `192.168/16`, and especially
  `169.254.169.254` (the cloud metadata endpoint — the classic path to stealing IAM
  credentials). Re-check **after** redirects, or disable them.

## 7. Web-layer basics

- **XSS**: autoescape on (module 16); `|safe` only for markup you generated.
- **CSRF**: a per-session token on every state-changing form; `SameSite=Lax` cookies.
- Cookies: `Secure`, `HttpOnly`, `SameSite`.
- Headers: `Content-Security-Policy`, `X-Content-Type-Options: nosniff`,
  `Strict-Transport-Security`, `Referrer-Policy`.
- **Authorisation ≠ authentication.** Check that *this* user may touch *this* object on
  every request — IDOR (`/orders/1234` belonging to someone else) is the most common real
  bug in the APIs you'll write.
- Rate-limit auth endpoints (module 09's token bucket), and never return different errors
  for "no such user" vs "wrong password" — that's a user-enumeration oracle.

## 8. Secrets management

- Not in source, not in the repo history, not in a `.env` that gets committed.
  `.gitignore` it and add `detect-secrets` or `gitleaks` to pre-commit.
- Environment variables at minimum; a secret manager (Vault, AWS/GCP Secrets Manager) for
  real systems, with rotation.
- Redact at the **logging formatter**, not at each call site (module 17) — you will
  forget a call site.
- Never put a secret in a URL: it lands in access logs, proxies, and `Referer` headers.

## 9. Supply chain

```bash
pip-audit                     # CVEs in your installed tree
uv pip compile --generate-hashes requirements.in     # pin + hash
uv lock                       # or a real lockfile
```

- Lock and hash-pin application dependencies; verify hashes on install.
- Beware **typosquatting** (`reqeusts`, `python-dateutils`) — check the name before adding.
- `pip install` runs arbitrary code from `setup.py` at INSTALL time. `--only-binary`
  reduces that surface.
- Review what a new dependency pulls in; a tiny package with 40 transitive deps is 40 more
  maintainers who can push code to your server.

## 10. Tooling to put in CI

| Tool | Finds |
|---|---|
| `bandit` | insecure API usage (`eval`, `shell=True`, weak hashes) |
| `ruff --select S` | the same Bandit rules, much faster |
| `pip-audit` / `safety` | known CVEs in dependencies |
| `detect-secrets`, `gitleaks` | committed credentials |
| `semgrep` | custom taint rules for your own sinks |
| `mypy --strict` | not a security tool, but kills a class of type-confusion bugs |

Enable `ruff`'s `S` ruleset on new code, then a `# noqa: S###` with a comment where you
genuinely need the risky call. The comment is the audit trail.

## 11. When you *are* the one being attacked

- Fail closed. On an unexpected error, deny — don't fall through to "allow".
- Validate at the boundary (pydantic, module 15), then trust your own types inside.
- Bound everything: request size, JSON depth, array lengths, regex input, upload size,
  pagination limits. Unbounded input is a denial-of-service.
- Log security events (auth failures, permission denials) with enough context to
  investigate, and *without* the credential itself.

## Exercises

`exercises_25.py`, then `pytest 25_security`. Everything here is defensive: password
storage, tokens, webhook verification, filename sanitising, SSRF/open-redirect guards, log
redaction, and bounded JSON parsing.

## Further reading

- [OWASP Top 10](https://owasp.org/www-project-top-ten/) and the [Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [`secrets`](https://docs.python.org/3/library/secrets.html), [`hmac`](https://docs.python.org/3/library/hmac.html), [`hashlib`](https://docs.python.org/3/library/hashlib.html)
- [Python Security docs](https://python-security.readthedocs.io/)
