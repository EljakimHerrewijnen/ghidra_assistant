# Track

## Session
- Date: 2026-04-02
- Goal: Add `utils/emulator` abstraction with `BaseEmulator(arch, mode, ...)`, backend adapters, and tests.

## Commands
1. `ls -la dump && find dump -maxdepth 4 -type f ...`
2. `find -L dump/emulator -type f ...`
3. `wc -l dump/emulator/*.py && tail -n 20 dump/emulator/unicorn_emulator.py`
4. `pytest -q tests/test_emulator_backends.py` (failed: pytest not installed)
5. `python3 -m unittest -q tests/test_emulator_backends.py` (failed import mode)
6. `python3 tests/test_emulator_backends.py -q` (passed; backend tests ran with skips)
7. `python3 - <<'PY' ... BaseEmulator.available_backends() ... PY` (sanity check)
8. `python3 -m py_compile utils/emulator/base_emulator.py utils/emulator/unicorn_backend.py utils/emulator/angr_backend.py tests/test_emulator_backends.py`

## Edited Files
- `track.md` (created and updated)
- `utils/emulator/__init__.py` (created)
- `utils/emulator/base_emulator.py` (created)
- `utils/emulator/unicorn_backend.py` (created)
- `utils/emulator/angr_backend.py` (created)
- `tests/test_emulator_backends.py` (created)

## Notes
- Reviewed reference backend design in symlinked `dump/emulator`.
- Added a backend-factory style `BaseEmulator(arch, mode, backend=...)` facade.
- Added Unicorn and angr adapters with shared API shape.
- Added unittest-based backend tests that double as usage examples.
