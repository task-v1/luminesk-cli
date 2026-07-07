---
sidebar_position: 12
---

# Development & Contributing

## Local setup

```bash
git clone https://github.com/task-v1/luminesk-cli
cd luminesk-cli
~/.local/bin/uv sync --locked --extra dev
```

## Quality checks

```bash
~/.local/bin/uv run ruff check .
~/.local/bin/uv run pytest
```

## Build smoke test

```bash
~/.local/bin/uv sync --locked --extra build
~/.local/bin/uv run pyinstaller --onefile --name luminesk luminesk/__main__.py
```

## Documentation maintenance checklist

Before opening/updating a pull request:

- [ ] Updated user-facing docs for any behavior/CLI/config/runtime changes.
- [ ] Verified command names, aliases, options, and outcomes match implementation.
- [ ] Added or updated troubleshooting entries for new failure modes.
- [ ] Added cross-links to avoid duplicated or conflicting instructions.
- [ ] Confirmed README links point to canonical docs pages.

## Documentation ownership expectations

Treat documentation changes as part of implementation completeness. If behavior changes and docs do not, the change is incomplete.
