---
name: fix-issue
description: Fix a GitHub issue end-to-end — read the issue, implement the fix, write tests, and create a PR
disable-model-invocation: true
argument-hint: "[issue-number]"
---

Fix GitHub issue #$ARGUMENTS.

1. Run `gh issue view $ARGUMENTS` to read the issue details and comments
2. Analyze the problem described — identify affected files and root cause
3. Search the codebase for relevant code using Grep and Glob
4. Implement the fix following project patterns:
   - Use structlog for logging, not print()
   - Raise AppError with appropriate ErrorCode for error cases
   - Add type hints to all function signatures
   - Follow existing code patterns in the same module
5. Write tests that reproduce the issue and verify the fix:
   - Unit tests in `tests/unit/` mirroring src/ structure
   - Integration tests in `tests/integration/` if API behavior changed
6. Run the full quality check:
   ```bash
   uv run ruff check src/ tests/ --fix && uv run mypy src/ --ignore-missing-imports && uv run pytest tests/ -x -q
   ```
7. Fix any lint, type, or test failures
8. Create a commit with a descriptive message referencing the issue:
   ```
   Fix #<issue-number>: <concise description>
   ```
9. Push the branch and create a PR with `gh pr create`
