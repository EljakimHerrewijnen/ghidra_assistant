from .utils.ghidra.ghidra_connect import *
from .utils.utils import *

class GhidraAssistant:
    def __init__(self, backend='auto') -> None:
        self.backend = backend
        self.setup()

    def setup(self):
        '''
        Setup GA
        '''
        self.ghidra = Ghidra(self.backend)

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