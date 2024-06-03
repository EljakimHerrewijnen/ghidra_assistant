from src.ghidra_assistant.ghidra_assistant import GhidraAssistant
from src.ghidra_assistant.utils.utils import *

def test():
    info("Running tests")
    ga = GhidraAssistant()
    
    # Test colouring lines
    # Generate a list of fake PC values from 0x4001ed94 to 0x4001ed94 + 0x1000
    pc_values = [0x4001ed94 + i for i in range(0, 0x1000, 4)]
    ga.ghidra.set_background_color(pc_values)
    ga.ghidra.clear_background_color()
    
if __name__ == "__main__":
    test()