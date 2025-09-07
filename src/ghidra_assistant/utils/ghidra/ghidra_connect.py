import ghidra_bridge

from ..utils import *
from ..definitions import *
import typing
from .ghidra_backend import GhidraBackend

class Ghidra(GhidraBackend):
    def __init__(self, backend):
        super().__init__()

        self.backend = backend
        if backend == 'auto':
            pass # TODO choose backend automatically
        elif backend == 'mcp':
            from .mcp_backend import MCPBackend
            self.backend = MCPBackend()
        elif backend == 'mcp_hydra':
            from .mcp_hydra import MCPHydraBackend
            self.backend = MCPHydraBackend()
        elif backend == 'pyhidra':
            from .pyhidra_backend import PyHidraBackend
            self.backend = PyHidraBackend()
        elif backend == 'ghidra_bridge':
            from .py3_bridge_backend import Py3BridgeGhidraBackend
            self.backend = Py3BridgeGhidraBackend()
        else:
            raise Exception("Unsupported")

    def __getattr__(self, item):
        """
        Redirect attribute access to the backend.
        """
        if hasattr(self.backend, item):
            return getattr(self.backend, item)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{item}'")

    def __setattr__(self, key, value):
        """
        Redirect attribute setting to the backend.
        """
        if key == 'backend':
            super().__setattr__(key, value)
            return
        if hasattr(self.backend, key):
            setattr(self.backend, key, value)
        else:
            super().__setattr__(key, value)

    @property
    def cursor(self) -> int:
        """
        Return the cursor for the current backend.
        """
        return self.backend.cursor

    