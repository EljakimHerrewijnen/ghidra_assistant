# Ghidra Assistant

## Concrete device


## Quick start: create a simple loader (map + write)

Below is a minimal example showing how to use the MCP Hydra backend to map a memory segment and write bytes into it from Python. This assumes the Ghidra HATEOAS plugin is running (for example at http://127.0.0.1:8192).

```python
from ghidra_assistant.ghidra_assistant import GhidraAssistant

# Start with the hydra backend
ga = GhidraAssistant(backend='mcp_hydra').ghidra

base_addr = 0x401000
segment_name = ".loader_data"
payload = b"\x7fELF..."  # your bytes here

# 1) Create/map a segment
ok = ga.memory_create_segment(
	name=segment_name,
	address=base_addr,
	size=max(0x1000, len(payload)),
	read=True,
	write=True,
	execute=False,
	overlay=False,
	initialized=True,
	fill=0
)
print("segment created:", ok)

# 2) Write the bytes into memory
ga.write_mem(base_addr, payload)

# 3) Read back a few bytes to verify
read_back = ga.read_memory(base_addr, 16)
print("first 16 bytes:", read_back.hex())
```

Notes:
- If your Ghidra server runs on a different host/port, set env vars GHIDRA_HYDRA_HOST and GHIDRA_HYDRA_PORT before running the script.
- The legacy 'mcp' backend is also available but may not support all features shown above.

