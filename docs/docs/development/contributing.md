# Contributing Guidelines

We welcome contributions to **Luminesk**! To maintain code quality, consistency, and stability, please adhere to the following guidelines when making changes.

---

## Code Quality Standards

- **Python Standards**: Follow PEP 8 style conventions.
- **Type Hinting**: All new functions, arguments, and return types must be fully type-hinted to enable clean static analysis checkouts.
- **Comments**: Maintain docstrings and inline comments for complex orchestrations (like process signal forwarding or indent-aware custom YAML parsers).

---

## Localization (i18n)

Luminesk supports multiple languages. If you add new user-facing messages, command options, or error panels:
1. **Identify the Key**: Create a unique dotted key (e.g. `cli.new_feature.option`).
2. **Translate Catalogs**: You must add the key and translated string to all translation catalogs under `Luminesk/core/locales/`:
   - `en.py` (English - default)
   - `ru.py` (Russian)
   - `uk.py` (Ukrainian)
   - `ja.py` (Japanese)
   - `zh.py` (Chinese)
3. **Prevent Crashes**: Leaving a language catalog without the key will cause fallback issues or crashes. Always populate all 5 files.

---

## Pull Request Process

1. **Branch Out**: Create a feature or bugfix branch from the **`dev`** branch (not `main`):
   ```bash
   git checkout dev
   git checkout -b feature/my-cool-addition
   ```
2. **Write Tests**: If you added utility functions, config helpers, or manager routines, write corresponding test cases inside the `tests/` directory.
3. **Verify Locally**: Run the test suites and linter checklist:
   ```bash
   uv run pytest
   ```
4. **Submit PR**: Open a Pull Request on GitHub targeting the **`dev`** branch. Include a clear description of the change, references to open issues, and proof of passing tests.
