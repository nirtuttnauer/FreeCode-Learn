# Contributing courses

Python Engineer's editable source is in `courses/python-engineer/source/`.
Its `course.json` supplies the stable course ID, display name and summary. To author
another Python track, create the same source layout in `courses/<your-course>/`,
add its course.json, and run `python3 scripts/build_python_engineer.py --course
courses/<your-course>`. The compiler allocates unused negative IDs and merges that
course into the existing catalog. Both apps and the runner discover its manifest
automatically. Keep workspace IDs and the generated ids.json when publishing updates.
Each ordered module supplies `README.md`, a demonstration `lesson_*.py`, starter
`exercises_*.py`, reference `solutions_*.py`, and required `test_*.py` checks.

The compiler turns each unfinished top-level function or class into a guided step.
Performance exercises marked `# <- fix this` are included too. Keep task names
stable: `courses/python-engineer/ids.json` permanently maps names to saved progress
IDs. Adding content appends IDs without renumbering existing steps.

Project specifications and editable `src/` packages live under `source/projects/`.
`project-checks/<project>.json` maps milestones to pytest selectors. Additional
required test files live beside the mapping, in a folder named for the project.
Every required milestone needs a nonempty selector group. Keep tests behavioral;
never trust a learner-generated report claiming its own implementation is correct.

Run `python3 scripts/build_python_engineer.py` using Python 3.12 or later. It emits
the step catalog, statements, shared starters and versioned execution manifest in
`data/learning/`. Do not edit generated JSON. The foundation-course builder also
regenerates Python Engineer so it cannot silently remove the new track.

The manifest records schemaVersion, stable step ID, workspace ID, entrypoint,
named check group, content version and pytest selectors. A workspace owns editable
file contents, trusted tests, optional demonstration and optional module reference.
Steps sharing a workspace share files; editing files invalidates their completion.
Required checks are immutable bundle resources; learner tests use test_learner*.py.
Timing checks use `@pytest.mark.benchmark` and run separately. Typing module checks
also require strict mypy. Grading requires nonempty passing checks; skips,
collection errors and stale submissions cannot complete a step.

Use build-time pinned dependencies only. Add wheel URLs/hashes for every target to
`packaging/course-packages-lock.json` and verify imports on all three platforms.
Tests use local databases, in-process HTTP clients, fake clocks and scripted models.

Create the shareable source with `python3 scripts/export_public.py --destination
<new-folder>`. This uses an allowlist, excluding private content and Git history.
Never make the personal repository public to distribute the course app.
