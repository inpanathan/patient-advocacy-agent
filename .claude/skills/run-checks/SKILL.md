---
name: run-checks
description: Run the full quality pipeline — lint, typecheck, and tests. Use after making changes to verify everything passes.
disable-model-invocation: true
---

Run the full quality pipeline and report results.

Execute each step sequentially, stopping on first failure:

```bash
echo "=== Ruff lint ===" && uv run ruff check src/ tests/
```

```bash
echo "=== Ruff format check ===" && uv run ruff format --check src/ tests/
```

```bash
echo "=== Mypy typecheck ===" && uv run mypy src/ --ignore-missing-imports
```

```bash
echo "=== Tests ===" && uv run pytest tests/ -x -q --tb=short
```

If any step fails:
1. Report which step failed and the error output
2. Suggest specific fixes
3. Ask whether to attempt the fixes automatically

If all steps pass, report success with a brief summary.
