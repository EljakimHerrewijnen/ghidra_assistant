# emulator/

Backend-agnostic emulator abstraction layer.

`BaseEmulator` is the public entry-point. It acts as a factory that selects a backend (e.g. `unicorn`, `angr`, `hedgehog`) and exposes a uniform API for memory and register access, code hooks, and execution control.

## Structure

| File | Purpose |
|------|---------|
| `base_emulator.py` | `BaseEmulator` facade + `EmulatorHook` base class |
| `unicorn_backend.py` | Unicorn-based backend (wraps `ARM64UC_Emulator` / `ARM_Emulator`) |
| `angr_backend.py` | angr-based backend (symbolic / concrete execution) |
| `hedgehog_backend.py` | Hedgehog-based backend (QEMU embedding API, board-backed arm64 first) |

## Adding a new backend

Implement the backend interface (see `unicorn_backend.py` as reference) and register it:

```python
BaseEmulator.register_backend("my_backend", create_my_backend)
```

The backend must provide at minimum: `mem_map`, `mem_unmap`, `mem_read`, `mem_write`, `mem_regions`, `emu_start`, `emu_stop`, `get_register`, `set_register`.

## Hedgehog notes

The Hedgehog backend is optional and currently scoped to board-backed AArch64 (`arch="arm64"`).

- Install `qemu.hedgehog` from the latest release wheel at https://github.com/EljakimHerrewijnen/qemu/releases/latest.
- Register reads and writes use target GDB register numbering internally, so the adapter performs explicit arm64 name-to-register mapping.
- The latest tested Hedgehog release (`v0.1.1a8`, package version `qemu 0.6.1a1`) fixes the unbounded `emu_start(begin, 0)` path.
- Repeated Hedgehog create/close cycles still abort the interpreter in one Python process, so keep tests and tooling to a single live Hedgehog instance per process.
- `mem_unmap`, `hook_mem_read`, and `hook_mem_write` are not currently exposed through the Hedgehog adapter.
