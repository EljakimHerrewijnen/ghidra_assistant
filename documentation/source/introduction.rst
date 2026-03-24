Introduction to the Ghidra Assistant
====================================

The Ghidra Assistant (GA) is a Python library that connects `Ghidra <https://github.com/NationalSecurityAgency/ghidra>`_ to bare-metal hardware targets and emulators. It is designed for firmware analysis and post-exploitation workflows, typically in combination with `Gupje <https://github.com/EljakimHerrewijnen/Gupje>`_, a small bare-metal stub debugger that runs directly on target hardware.

Core capabilities
*****************

- **Ghidra API** — a unified Python interface to Ghidra via multiple backends. The default backend is ``mcp_hydra``, which talks to the `ghydraMCP <https://github.com/LaurieWired/GhidraMCP>`_ Ghidra plugin.
- **ConcreteDevice** — abstraction for communicating with a real hardware target over a PEEK/POKE protocol. The device-side counterpart is implemented in Gupje.
- **Architecture debugger** — host-side logic for ARM64, ARM, and ARM Thumb that controls a Gupje stub running on the target: set up the vector table, read/write registers and memory, insert breakpoints, restore execution.
- **Emulator layer** — thin wrapper on top of Unicorn that loads memory and register state from a Ghidra project or a concrete device snapshot.

Typical workflow
****************

1. Gain code execution on the target (e.g. bootrom exploit, UART console).
2. Upload and execute the Gupje stub, which provides PEEK/POKE over USB or UART.
3. Use ``ConcreteDevice`` + the GA architecture debugger to interact with the device from Python: read memory, set breakpoints via the vector table, sync register state with Ghidra.
4. Optionally snapshot the device state and replay it in the Unicorn emulator for offline analysis.

Supported architectures
***********************

- ARM64 (AArch64) — EL3/EL1 debugger, MMU parsing, VBAR-based breakpoints
- ARM Thumb — basic register state, VBAR-based breakpoints
- ARM — minimal support
