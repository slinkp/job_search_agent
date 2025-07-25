- Never re-order functions, methods, or classes in a file
  unless explicitly asked to do so.

- Do not change or remove existing comments unless the code
  has changed in such a way that the comment is no longer valid.

- When adding functionality, always look for opportunities to re-use
  code that already exists. If unsure, suggest the possible re-use.

- When asked to refactor, assume the following guidelines:
  - Break the refactoring into small steps.
  - Make the smallest change possible at each step.
  - Make no other changes to the code except those strictly
    necessary to achieve the refactoring.
  - The code should behave logically identical before and
    after the refactoring, except insofar as the refactoring
    involves interface changes (signatures, return types, etc).
  - If there are tests, also update the tests if and only if
    signatures of tested methods/functions were changed, or
    new classes added. Suggest tests of newly created
    functions/methods/classes.

- Python-specific conventions:
  - Use Python type annotations whenever possible.
  - When creating tests for Python code:
    - Use pytest conventions instead of unittest.
    - Each test case should test one behavior.
    - Use `mock` to avoid interacting with external resources
      (APIs, files, network resources, etc).
    - When creating mocks via `patch`, always use `autospec=True`.
    - When instantiating Mock or MagicMock directly, pass a `spec` whenever possible.
    - Use pytest fixtures to organize repetitive mocking or setup.

## Logging

- All Python applications log to both console and files by default
- Log files are stored in the `logs/` directory at the project root
- Log files are rotated when they reach 10MB, with up to 5 backup files kept
- Log format includes timestamp, process name, process ID, log level, and message
- Log file names correspond to the process: `research_daemon.log`, `server.log`, etc.
