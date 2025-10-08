from .utils.ghidra.ghidra_connect import *  # noqa: F401,F403
from .utils.utils import *  # noqa: F401,F403


class GhidraAssistant:
    def __init__(self, backend: str = 'auto', **backend_kwargs) -> None:
        """High-level assistant wrapper.

        Parameters
        ----------
        backend: str
            Which backend to use ('mcp_hydra', 'mcp', 'pyhidra', 'ghidra_bridge', or 'auto').
        **backend_kwargs:
            Extra keyword arguments forwarded to the backend constructor where supported.
            For the 'mcp_hydra' backend this can include:
              - host: str
              - port: int
              - project_name: str
              - file_name: str
        """
        self.backend = backend
        self.backend_kwargs = backend_kwargs
        self.setup()

    def setup(self):
        """Instantiate the underlying Ghidra backend."""
        self.ghidra = Ghidra(self.backend, **self.backend_kwargs)

def main():
    '''
    Run some tests to see functionality
    '''
    info("Running tests")
    ga = GhidraAssistant()

    # Test colouring lines
    # Generate a list of fake PC values from 0x4001ed94 to 0x4001ed94 + 0x1000
    pc_values = [0x4001ed94 + i for i in range(0, 0x1000, 4)]
    ga.ghidra.set_background_color(pc_values, "red")

    dat = ga.ghidra.get_ghidra_memory_maps()
    pass
    # Test concrete device

    # Test emulators


if __name__ == "__main__":
    main()