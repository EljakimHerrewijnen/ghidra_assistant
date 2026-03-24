# Ghidra Backends

Code that connects to Ghidra. All backends implement the `GhidraBackend` interface (`ghidra_backend.py`).

## Backends

| File                    | Backend name    | Description |
|-------------------------|-----------------|-------------|
| `mcp_hydra.py`          | `mcp_hydra`     | **Default.** HATEOAS REST API via the ghydraMCP plugin |
| `mcp_backend.py`        | `mcp`           | Simple HTTP MCP server |
| `py3_bridge_backend.py` | `ghidra_bridge` | Legacy Python bridge (ghidra_bridge) |
| `pyhidra_backend.py`    | `pyhidra`       | Headless/embedded Ghidra |

Select a backend by name when constructing `GhidraAssistant`:

```python
from ghidra_assistant.ghidra_assistant import GhidraAssistant
ga = GhidraAssistant('mcp_hydra')
```

