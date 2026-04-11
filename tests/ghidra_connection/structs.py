
import sys
from ghidra_assistant.ghidra_assistant import GhidraAssistant

ga = GhidraAssistant(backend="mcp_hydra", file_name=sys.argv[1])

for struct in ga.ghidra.structs:
    print(struct)