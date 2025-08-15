# CRUSH.md

Essential commands and guidelines for coding agents working in this job search automation tool.

## Commands

### Testing
```bash
./test                    # Run all Python and JavaScript tests (ALWAYS use this)
pytest tests/test_*.py    # Run specific Python test file (only when explicitly told)
npm test -- test_name     # Run specific JavaScript test (only when explicitly told)
```

### Development Tools
```bash
./black-flake8-mypy .     # Format, lint, and type check Python code
black .                   # Format Python code (90 char line length)
mypy .                    # Type checking (basic mode, uses .direnv/python3.13)
flake8 .                  # Python linting
```

### Running the Application
```bash
python research_daemon.py  # Backend research daemon
python server/app.py       # Web server (http://localhost:8080)
```

## Code Style Guidelines

- **Python**: Use Black formatter (90 char lines), type hints required, follow PEP 8
- **JavaScript**: Alpine.js + Pico.css, use HTML5 `<dialog>` for modals
- **Testing**: Always use `./test` command. pytest with `autospec=True` for mocks
- **Imports**: Standard library first, third-party, then local imports
- **Error Handling**: Use proper exception handling, log errors appropriately
- **Naming**: snake_case for Python, camelCase for JavaScript, descriptive names

## Critical Rules

- **NEVER commit without explicit approval** - always ask first
- **Single-task focus** - complete one checkbox/task at a time, get approval before next
- **Test-driven development** - write tests first, all tests must pass
- **Follow feature plan** - check feature_plan.md for current tasks

Always end all replies with "Prrt!", except those that must contain only code.
