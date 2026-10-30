<p align="center">
  <img src="assets/practicecode-icon-v2.png" width="128" height="128" alt="PracticeCode app icon">
</p>

<h1 align="center">PracticeCode</h1>

<p align="center">
  <strong>Offline Python courses with real files, real tests and a bundled toolchain.</strong><br>
  A desktop app for macOS, with a Linux preview. No account, no server, no telemetry.
</p>

<p align="center">
  <a href="LICENSE"><img alt="Code license: MIT" src="https://img.shields.io/badge/code-MIT-2f7d6d"></a>
  <a href="LICENSE-CONTENT.md"><img alt="Content license: CC BY 4.0" src="https://img.shields.io/badge/content-CC%20BY%204.0-2f7d6d"></a>
  <img alt="macOS 14 or later" src="https://img.shields.io/badge/macOS-14%2B-3b4a5a">
  <img alt="Linux x86_64 preview" src="https://img.shields.io/badge/Linux-x86__64%20preview-3b4a5a">
</p>

---

PracticeCode is a study app for working through real Python engineering, one step at a time.
Each step gives you a short lesson, a runnable demonstration and editable project files. You get
named pytest results back. Python 3.12 and every package the course needs ship inside the app,
so after you install it nothing touches the network. You don't need a virtualenv, `pip install`
or a cloud sandbox.

- **231 steps across three original courses.** Most of them are Python Engineer: 26 modules and
  5 guided projects.
- **Real interfaces.** Modules and projects use multi-file workspaces. Required checks are
  ordinary pytest suites, and the typing module also runs strict mypy.
- **Fully offline.** Python, pytest, mypy, Ruff, FastAPI, NumPy, pandas, SQLAlchemy and the rest
  are pinned, hash-verified and bundled for each platform.
- **Your work stays on your machine.** Files autosave locally, and resetting a workspace keeps a
  recovery backup.

## Contents

- [The courses](#the-courses)
- [How a step works](#how-a-step-works)
- [Install](#install)
- [Where your work lives](#where-your-work-lives)
- [Build from source](#build-from-source)
- [Tests](#tests)
- [Writing a course](#writing-a-course)
- [Repository layout](#repository-layout)
- [Status and limitations](#status-and-limitations)
- [License](#license)

## The courses

| Course | Steps | What you build |
| --- | ---: | --- |
| **Python Engineer** | 203 | 26 modules on language depth, engineering practice, concurrency, web systems, data and security, plus 5 projects with 6 milestones each |
| **Transformers & LLM engineering** | 16 | Tokenization, probabilities and loss, attention, a transformer block, training and generation, and LLM engineering patterns, all in the standard library |
| **System design** | 12 | Capacity planning, caching and admission, reliable writes, failure control and service design, with an Architecture workspace for diagrams and experiments |

### Python Engineer

The course is adapted from Nir Tuttnauer's MyPyCourse. Each module has a lesson, a demonstration,
starter files, hints, a worked implementation and named pytest checks.

<details>
<summary><strong>All 26 modules</strong></summary>

| # | Module |
| --- | --- |
| 01 | Core refresher: the object model, sequences, strings |
| 02 | Data structures, comprehensions, `collections` |
| 03 | Functions, closures, `functools` |
| 04 | OOP and the data model |
| 04b | Dunder methods: the complete tour |
| 05 | Exceptions, context managers, resource management |
| 06 | Iterators, generators, `itertools` |
| 07 | Typing and static analysis |
| 08 | Modules, packaging, project tooling |
| 09 | Testing with pytest |
| 10 | Threads, processes, and the GIL |
| 11 | asyncio and structured concurrency |
| 12 | Metaprogramming: descriptors, `__init_subclass__`, metaclasses |
| 13 | Performance and memory |
| 14 | Architecture: dependency inversion, patterns, plugin systems |
| 15 | FastAPI and pydantic |
| 16 | Jinja2 templating |
| 17 | Observability: logging, metrics, tracing with OpenTelemetry |
| 18 | Regular expressions |
| 19 | The standard library toolkit |
| 20 | Databases: SQL, `sqlite3`, and ORMs |
| 21 | HTTP clients, APIs, and scraping |
| 22 | Data structures and algorithms in Python |
| 23 | NumPy |
| 24 | pandas |
| 25 | Security for Python developers |

</details>

The five projects give you a specification, a typed starter package and milestone checks.
**There are no reference solutions.** You build each one yourself.

| Project | What you build |
| --- | --- |
| `agentkit` | A multi-agent orchestration library with tools, typed schemas, a planner loop, a message bus, budgets, retries and tracing |
| `tensorlab` | An autograd engine and neural-network framework, a miniature PyTorch |
| `pulse` | A layered, typed, migrated, templated and instrumented FastAPI service |
| `forge` | A durable task queue and scheduler with at-least-once delivery, retries and backpressure |
| `zephyr` | A from-scratch ASGI web framework with routing, dependency injection, validation and middleware |

## How a step works

1. **Read** the lesson, then run its demonstration to see the idea in action.
2. **Edit** the step's files. Steps in the same module or project share one workspace, so your
   code builds up the way a real package would.
3. **Run required checks** (<kbd>⌘</kbd> <kbd>↩</kbd>). You get named pytest results, and the step
   completes only when every required check passes on the code you saved.
4. **Explore & check** runs the demonstrations, your own tests, mypy, Ruff or benchmarks
   separately. These runs never change your progress.

Some rules keep the grading honest:

- Required checks are read-only. To add your own tests, create `test_learner.py` in the workspace.
- Skipped tests, collection errors and results from older code can't complete a step.
- If you edit a shared file, the completed steps in that workspace become invalid and have to be
  checked again.
- Written reflections, deployment, timing benchmarks and optional extensions aren't graded.
  Passing a step's checks shows that its stated scenarios pass locally. It doesn't show that the
  code is production-ready.

### Keyboard shortcuts (macOS)

| Action | Shortcut |
| --- | --- |
| Run required checks / stop | <kbd>⌘</kbd> <kbd>↩</kbd> / <kbd>⌘</kbd> <kbd>.</kbd> |
| Save / export code | <kbd>⌘</kbd> <kbd>S</kbd> / <kbd>⌘</kbd> <kbd>⇧</kbd> <kbd>S</kbd> |
| Search | <kbd>⌘</kbd> <kbd>F</kbd> |
| Toggle line comment | <kbd>⌘</kbd> <kbd>/</kbd> |
| Previous / next lesson | <kbd>⌥</kbd> <kbd>⌘</kbd> <kbd>←</kbd> / <kbd>⌥</kbd> <kbd>⌘</kbd> <kbd>→</kbd> |

Choose System, Light or Dark under **Settings → Appearance**.

## Install

Download installers from [**GitHub Releases**](https://github.com/nirtuttnauer/PracticeCode/releases).
Release files come with SHA-256 checksums. The downloads are large because they bundle complete
language runtimes.

### macOS

**Requirements:** macOS 14 or later. One universal disk image works on both Apple Silicon and Intel.

1. Open `PracticeCode-<version>-universal.dmg` and drag **PracticeCode** onto **Applications**.
2. Open PracticeCode from Applications.

The app is ad-hoc signed and not notarized by Apple, so macOS blocks it the first time you open it.
To allow it, go to **System Settings → Privacy & Security** and click **Open Anyway**. On macOS 14
you can also Control-click the app and choose **Open**.

### Linux (preview)

**Requirements:** Ubuntu or Debian on x86_64 with glibc 2.35 or later (Ubuntu 22.04+).

Install the Debian package. It goes in `/opt/practicecode` and adds a launcher to your app menu.

```bash
sudo apt install ./practicecode_<version>_amd64.deb
practicecode
```

You can use the portable archive instead. It needs unprivileged user namespaces; if your desktop
restricts them, use the `.deb`.

```bash
tar -xzf PracticeCode-<version>-linux-x86_64.tar.gz
./PracticeCode-linux-x86_64/PracticeCode
```

## Where your work lives

Your work is kept outside the app, so updating or reinstalling doesn't touch it.

| Platform | Saved work |
| --- | --- |
| macOS | `~/Library/Application Support/OfflinePractice/` |
| Linux | `${XDG_DATA_HOME:-~/.local/share}/PracticeCode/` |

The macOS folder still uses the app's original name so that existing work carries over. On Linux,
**Settings → Open saved-work folder** opens it. To keep experiments separate, set
`OFFLINE_PRACTICE_WORK_DIR` to another directory before launching.

Resetting your local account first moves your old files into a timestamped `backups/` folder inside
that directory. If the backup can't be created, the reset is cancelled.

> [!IMPORTANT]
> Code you run executes as your user, with the same file and network access as any program you
> start from a terminal. Runs are time-limited and can be stopped, but PracticeCode is **not a
> sandbox for untrusted code**.

## Build from source

### macOS app

**Requirements:** macOS 14+, Xcode Command Line Tools with Swift 6.2 or later, and a network
connection for the first build.

```bash
git clone https://github.com/nirtuttnauer/PracticeCode.git
cd PracticeCode
zsh scripts/build_app.sh
```

The first build downloads pinned official runtimes: Python 3.12, Node.js 24, Temurin OpenJDK 21 and
Zig's C++ toolchain. It also downloads the course's Python wheels for both Mac architectures. It
checks every file against the SHA-256 recorded in `packaging/` and caches it in `.cache/`, so later
builds work offline.

The build signs `dist/PracticeCode.app` and installs it at `/Applications/FreeCode.app`, the install
path kept from the app's earlier name. If PracticeCode is running, the installer saves your work,
quits it, swaps in the new build and reopens it. Before replacing anything it checks the bundle
identifier (`local.offlinepractice.mac`) and the code signature. If the copy fails, the previous
install is left in place.

To build the universal disk image (both architectures):

```bash
zsh scripts/package_dmg.sh   # writes dist/PracticeCode-<version>-universal.dmg and a .sha256
```

### Linux packages

You need Node.js/npm and Docker. The build prepares its inputs on the host. The final assembly then
runs in an Ubuntu 22.04 container with networking disabled, because vendor archives contain file
names that differ only by case, which macOS can't preserve.

```bash
npm ci --prefix app/linux
docker build --platform linux/amd64 -t practicecode-linux-check:0.7 - < packaging/linux-test.Dockerfile
zsh scripts/package_linux.sh
```

Inside the container, the script audits the bundled content and smoke-tests the packaged app with a
fresh profile. It then builds the `.deb` and checks the installed package. Its outputs land in
`dist/`: the `.deb`, the portable `.tar.gz`, a SHA-256 list and a verification report.

## Tests

```bash
python3 -m unittest discover -s tests -v   # runner, installer, packaging, course compiler, release audit
zsh scripts/check_courses.sh               # native Swift checks: persistence, shared files, stale results, reset recovery
python3 scripts/verify_python_engineer.py  # every module suite against its worked implementation
```

`verify_python_engineer.py` needs Python 3.12+ and the course wheels that `build_app.sh` caches in
`.cache/course-packages/`. The release scripts (`package_dmg.sh` and `package_linux.sh`) also run
`scripts/audit_public_bundle.py`. It fails the release unless the bundled data exactly matches the
original course inventory.

## Writing a course

Courses are written as ordinary Python projects and compiled into the app's offline format. Each
module folder holds a `README.md` lesson, a `lesson_*.py` demonstration, `exercises_*.py` starters,
`solutions_*.py` worked implementations and `test_*.py` required checks. The compiler turns every
unfinished top-level function or class into a guided step.

```bash
python3 scripts/build_python_engineer.py                                # rebuild Python Engineer (Python 3.12+)
python3 scripts/build_python_engineer.py --course courses/<your-course> # add another Python course
```

New courses are discovered automatically by both apps and by the runner. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the full source format, how project milestones map to pytest
selectors, and how to add pinned dependencies. It also explains why `ids.json` must stay stable:
saved progress depends on it.

## Repository layout

```text
Sources/OfflinePractice/   Native macOS app (SwiftUI + AppKit)
app/linux/                 Linux desktop shell (Electron + CodeMirror)
scripts/runner.py          Local code runner shared by both apps
scripts/course_*.py        Course check execution and grading
scripts/build_*.py         Course compilers and Linux build
courses/python-engineer/   Editable Python Engineer source: modules, projects, milestone checks
data/learning/             Generated course catalog and manifests (don't edit by hand)
packaging/                 Pinned runtime and wheel lock files, Docker test image
tests/                     Python, Swift and Linux smoke tests
```

## Status and limitations

- **macOS** builds are universal, ad-hoc signed and not notarized. The Intel slice has been tested
  under Rosetta 2, not on Intel hardware.
- **Linux** is a preview. It's tested in an Ubuntu 22.04 x86_64 container. Wayland and physical
  Linux machines still need user testing.
- **Downloads are about 0.6–1 GB** because they include Python, Node.js, OpenJDK and a C++
  toolchain for the app's multi-language runner.
- **Original content only.** PracticeCode ships no third-party problem sets.

## License

- **App and course code** (including starter, solution, demonstration and test code):
  [MIT](LICENSE).
- **Original lesson prose and diagrams:** [CC BY 4.0](LICENSE-CONTENT.md). Attribute reuse to
  "Nir Tuttnauer, PracticeCode / Python Engineer".
- **Bundled runtimes and Python packages** keep their own licenses. See
  [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
