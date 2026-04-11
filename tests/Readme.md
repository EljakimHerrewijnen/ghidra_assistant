# Tests

Repository test suites and executable examples live here.

## Layout

- `unit/` - fast unit tests for core modules and backends.
- `arm64/` - architecture-focused emulator tests/examples.
- `ghidra_connection/` - runnable example project for Ghidra connection workflows.

## Run

```bash
pdm run python -m pytest -q
```
