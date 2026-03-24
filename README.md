# Ghidra Assistant

A Python toolkit that bridges [Ghidra](https://github.com/NationalSecurityAgency/ghidra) with bare-metal debuggers, emulators, and hardware targets. Designed to work alongside [Gupje](https://github.com/EljakimHerrewijnen/Gupje), a bare-metal stub debugger for post-exploitation workflows on embedded/ARM devices.

## What it does

- Provides a unified Python API for Ghidra via swappable backends (default: `mcp_hydra`)
- Interfaces with `ConcreteDevice` targets over a simple PEEK/POKE protocol (implemented by Gupje on the device side)
- Supports ARM64, ARM, and ARM Thumb architectures for debugger and emulator workflows
- Integrates with Unicorn-based emulators for hardware-in-the-loop and snapshot-based analysis

## Backends

| Backend        | Description |
|----------------|-------------|
| `mcp_hydra`    | **Default.** Connects to the [ghydraMCP](https://github.com/LaurieWired/GhidraMCP) Ghidra plugin via its HATEOAS HTTP API. Supports multiple open Ghidra instances. |
| `mcp`          | Connects to a simple HTTP server plugin for Ghidra. |
| `ghidra_bridge`| Legacy Python-2-to-3 bridge via `ghidra_bridge`. |
| `pyhidra`      | Headless/embedded Ghidra via `pyhidra`. |

## Development with PDM

This project uses [PDM](https://pdm-project.org/) for packaging and dependency management.

```bash
# Install PDM (one-time)
pipx install pdm

# Create and sync the environment
pdm sync -d

# Run the module
pdm run python -m ghidra_assistant.ghidra_assistant

# Use the console script
pdm run ghidra-assistant

# Build wheels/sdist
pdm build
```

## Quick start

```python
from ghidra_assistant.ghidra_assistant import GhidraAssistant

# Connect to Ghidra via the mcp_hydra backend (default)
ga = GhidraAssistant()

# List functions
for fn in ga.ghidra.functions:
    print(fn.name, fn.address)

# Read memory
data = ga.ghidra.read_memory(0x401000, 64)
```

See `src/ghidra_assistant/Readme.md` for more examples including memory mapping and writing.
