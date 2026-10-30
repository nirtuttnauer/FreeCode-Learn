# PracticeCode

An open-source, offline coding and learning desktop app. Native SwiftUI/AppKit on
macOS 14+, with an Electron preview for Ubuntu/Debian x86_64. No account, server,
telemetry, or downloads while studying.

## Python Engineer

26 Python modules and five guided projects, adapted from Nir Tuttnauer's MyPyCourse.
Study a concept, run its demonstration, edit real Python files, and get named pytest
results. Covers the object model, typing, concurrency, asyncio, metaprogramming,
performance, architecture, FastAPI, templates, observability, databases, NumPy,
pandas, and security. Projects build an agent library, autograd framework, web
service, durable queue and ASGI framework.

Module exercises have worked implementations; projects offer specifications,
milestones and checks. Written reasoning, deployment, timing benchmarks and
optional extensions are ungraded. Passing checks means the specified local
scenarios pass, not that a service is production-ready.

The original Transformers & LLM engineering and System design tracks are included.
The public app contains no imported LeetCode library.

## Downloads

Installers for macOS (Apple Silicon and Intel) and Linux are available on the
[GitHub Releases page](https://github.com/nirtuttnauer/PracticeCode/releases).
Releases contain original courses only; no LeetCode library, personal work or private history.

## Build

macOS requires Command Line Tools with Swift 6.2+. Run:

```sh
zsh scripts/build_app.sh
```

The compatibility bundle identifier and saved-work directory remain unchanged across this rename.

Build-time downloads are checksum-pinned and cached. Both Mac architectures receive
their own Python course dependencies. The build signs and installs PracticeCode at
`/Applications/FreeCode.app`, preserving `local.offlinepractice.mac` and saved work
in `~/Library/Application Support/OfflinePractice/`.

For Linux, install Node/npm build tools and use `zsh scripts/package_linux.sh`.
Final Linux assembly runs on Linux; see the script for container inputs.

## Authoring and checks

See CONTRIBUTING.md for the source format. Regenerate the course with Python 3.12+:

```sh
python3 scripts/build_python_engineer.py
python3 -m unittest discover -s tests -p 'test_course*.py' -v
python3 -m unittest discover -s tests -p 'test_python_engineer.py' -v
```

Personal work stays outside the installed bundle. Workspace reset makes a recovery
backup. Code runs with your user permissions and is not a sandbox for untrusted
programs. Stop and bounded execution are available.

## License

App and course code: MIT. Original lesson prose and diagrams: CC BY 4.0, attributed
to Nir Tuttnauer. See LICENSE, LICENSE-CONTENT.md and THIRD_PARTY_NOTICES.md.
