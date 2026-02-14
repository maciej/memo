# Repository Guidelines

## Project Structure

- `src/memo/`: CLI entrypoint and Click command definitions (`memo`).
- `src/memo_helpers/`: Apple Notes/Reminders integrations (mostly `osascript` calls) plus helper utilities.
- `test/`: pytest-based CLI tests (Click `CliRunner`).
- `docs/` + `mkdocs.yml`: project documentation (MkDocs).
- `.github/`: repo assets (images, workflows).

## Build, Test, and Development Commands

This is a Python package (requires Python `>=3.13`) and uses `uv` for local development.

- `uv venv && source .venv/bin/activate`: create/activate a virtualenv.
- `uv sync`: install dependencies from `pyproject.toml`/`uv.lock`.
- `uv tool install . -e`: install `memo` in editable mode for local CLI testing.
- `memo --help`: run the CLI after installation.
- `uv run pytest`: run the test suite.
- `uv sync --extra docs && uv run mkdocs serve`: install docs deps and serve docs locally.

## Coding Style & Naming Conventions

- Python: 4-space indentation, PEP 8 conventions, `snake_case` for modules/functions.
- Keep AppleScript snippets readable and localized to helper modules (avoid duplicating script strings).
- Prefer small, single-purpose helpers in `src/memo_helpers/` over adding complexity to `src/memo/memo.py`.

## Testing Guidelines

- Framework: `pytest` (configured in `pyproject.toml`).
- Tests live in `test/` and typically use Click’s `CliRunner`.
- Naming: follow the existing pattern `test/memo_*_test.py` and `def test_*():`.
- When adding commands/flags, add at least one CLI-level test asserting `exit_code` and a stable output substring.

## Commit & Pull Request Guidelines

- Commit messages: follow Conventional Commits when possible (`feat: ...`, `fix: ...`, `docs: ...`), per `CONTRIBUTING.md`.
- PRs should include: what changed, why, how to test (exact commands), and any user-facing output changes (paste terminal output or attach a short GIF for UX changes).

## Platform Notes (Important)

- Memo automates Apple Notes/Reminders via `osascript`, so most functionality is macOS-only.
- Expect macOS privacy prompts (Automation access) on first run; document new prompts/permissions in PRs when relevant.
