"""Backend selection and delegation for GhidraAssistant.

Dynamic imports are used so optional dependencies (e.g., ghidra_bridge)
don't raise ImportError unless that backend is chosen.
"""

from ..utils import *
from ..definitions import *
import typing
from .ghidra_backend import GhidraBackend

class Ghidra(GhidraBackend):
    def __init__(self, backend: str, **backend_kwargs):
        super().__init__()

        self.backend_name: str = backend
        self._impl: typing.Any
        if backend == 'auto':
            # Attempt hydra first
            try:
                from .mcp_hydra import MCPHydraBackend  # type: ignore
                self._impl = MCPHydraBackend(**backend_kwargs)
                self.backend_name = 'mcp_hydra'
            except Exception:  # pragma: no cover
                from .mcp_backend import MCPBackend
                self._impl = MCPBackend()
                self.backend_name = 'mcp'
        elif backend == 'mcp':
            from .mcp_backend import MCPBackend
            self._impl = MCPBackend()
        elif backend == 'mcp_hydra':
            from .mcp_hydra import MCPHydraBackend
            self._impl = MCPHydraBackend(**backend_kwargs)
        elif backend == 'ghidra_bridge':
            from .py3_bridge_backend import Py3BridgeGhidraBackend
            self._impl = Py3BridgeGhidraBackend()
        else:
            raise Exception("Unsupported backend: " + backend)

    def __getattr__(self, item):
        """
        Redirect attribute access to the backend.
        """
        if hasattr(self._impl, item):
            return getattr(self._impl, item)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{item}'")

    def __setattr__(self, key, value):
        """
        Redirect attribute setting to the backend.
        """
        if key in ('backend_name', '_impl'):
            super().__setattr__(key, value)
            return
        if key not in ('backend',):  # allow old attribute but treat specially
            try:
                if hasattr(self, '_impl') and hasattr(self._impl, key):
                    setattr(self._impl, key, value)
                    return
            except Exception:  # pragma: no cover
                pass
        else:
            super().__setattr__(key, value)

    @property
    def cursor(self) -> int:
        """
        Return the cursor for the current backend.
        """
        return getattr(self._impl, 'cursor', 0)

