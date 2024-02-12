from .utils.ghidra.ghidra_connect import *
from .utils.utils import *

class GhidraAssistant:
    def __init__(self) -> None:
        self.setup()

    def setup(self):
        '''
        Setup GA
        '''
        self.ghidra = Ghidra()

def main():
    '''
    Run some tests to see functionality
    '''
    info("Running tests")
    ga = GhidraAssistant()
    dat = ga.ghidra.get_ghidra_memory_maps()

    # Test concrete device

    # Test emulators


if __name__ == "__main__":
    main()