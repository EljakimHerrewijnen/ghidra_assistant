from ....concrete_device import *
from .asm_arm64 import *

INSTRUCTION_SIZE = 4

class ARM64Stepper:
    def __init__(self, cd : ConcreteDevice , pc, debug=False) -> None:
        self.cd = cd
        self.sc : ShellcodeCrafter = self.cd.arch_dbg.sc
        self.pc = pc
        self.debug = debug
        
    def step(self):
        # Fetch instruction
        hook_block = self.cd.memdump_region(self.pc, 0x14)
        
        if self.debug:
            print(self.sc.disasm_bytes(hook_block, self.pc))
        
        # Decode instruction
        instr_decoded =  self.sc.disasm_bytes(hook_block[:INSTRUCTION_SIZE], self.pc)
        
        # Place the debugger hook at pc + INSTRUCTION_SIZE
        self.cd.memwrite_region(self.pc + INSTRUCTION_SIZE, self.cd.arch_dbg.sc.branch_absolute(self.cd.arch_dbg.debugger_addr))
        self.cd.restore_stack_and_jump(self.pc)
        assert self.cd.read(4) == b"GiAs", "Stepping failed to return to debugger!"
        
        # Restore overwritten code
        self.cd.memwrite_region(self.pc, hook_block[INSTRUCTION_SIZE:])
        
        # print the code that was executed
        self.pc += INSTRUCTION_SIZE
        print(instr_decoded)
        pass
    
    def run(self, start):
        self.pc = start
        # TODO figure out when to stop, for example when a function has returned
        while True:
            self.step()
        pass