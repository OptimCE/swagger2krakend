# AGENTS.md

## Code Quality

Always run **ruff** and **black** to lint and format code before committing:

```bash
uv run ruff check .
uv run black .
```

- **ruff** replaces flake8 for linting (configured in `pyproject.toml`)
- **black** handles code formatting (line length: 120)

Run both tools on any Python files you create or modify.
