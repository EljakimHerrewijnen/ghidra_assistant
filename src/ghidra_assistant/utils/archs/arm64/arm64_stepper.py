from ....concrete_device import *
from .asm_arm64 import *

INSTRUCTION_SIZE = 4

class ARM64Stepper:
    def __init__(self, cd : ConcreteDevice , pc, debug=False) -> None:
        self.cd = cd
        self.sc : ShellcodeCrafter = self.cd.arch_dbg.sc
        self.pc = pc
        self.debug = debug
        self.saved_pcs = {}
        
    def get_next_addr(self) -> int:
        c_insn = self.cd.memdump_region(self.pc, 4)
        c_insn_decoded = next(self.sc.cs.disasm(c_insn, self.pc))
        
        # Check if it is a branch instruction
        if c_insn_decoded.mnemonic == "b":
            target = c_insn_decoded.operands[0].value.imm
            return target
        elif c_insn_decoded.mnemonic == "bl":
            target = c_insn_decoded.operands[0].value.imm
            return target
        # Also all conditional branches
        elif c_insn_decoded.mnemonic == "b.eq":
            target = c_insn_decoded.operands[0].value.imm
            # Check if condition is met using R_NZCV register in self.cd.arch_dbg.state.R_NZCV
            if self.cd.arch_dbg.state.NZCV & 0b0001:
                return target
        elif c_insn_decoded.mnemonic == "b.ne":
            target = c_insn_decoded.operands[0].value.imm
            # Check if condition is met using R_NZCV register in self.cd.arch_dbg.state.R_NZCV
            if not self.cd.arch_dbg.state.NZCV & 0b0001:
                return target
        elif c_insn_decoded.mnemonic == "b.hs":
            target = c_insn_decoded.operands[0].value.imm
            # Check if condition is met using R_NZCV register in self.cd.arch_dbg.state.R_NZCV
            if self.cd.arch_dbg.state.NZCV & 0b1000:
                return target
        elif c_insn_decoded.mnemonic == "b.lo":
            target = c_insn_decoded.operands[0].value.imm
            # Check if condition is met using R_NZCV register in self.cd.arch_dbg.state.R_NZCV
            if not self.cd.arch_dbg.state.NZCV & 0b1000:
                return target
        elif c_insn_decoded.mnemonic == "b.mi":
            target = c_insn_decoded.operands[0].value.imm
            # Check if condition is met using R_NZCV register in self.cd.arch_dbg.state.R_NZCV
            if self.cd.arch_dbg.state.NZCV & 0b0100:
                return target
        elif c_insn_decoded.mnemonic == "b.pl":
            target = c_insn_decoded.operands[0].value.imm
            # Check if condition is met using R_NZCV register in self.cd.arch_dbg.state.R_NZCV
            if not self.cd.arch_dbg.state.NZCV & 0b0100:
                return target
        elif c_insn_decoded.mnemonic == "b.vs":
            target = c_insn_decoded.operands[0].value.imm
            # Check if condition is met using R_NZCV register in self.cd.arch_dbg.state.R_NZCV
            if self.cd.arch_dbg.state.NZCV & 0b0010:
                return target
        elif c_insn_decoded.mnemonic == "b.vc":
            target = c_insn_decoded.operands[0].value.imm
            # Check if condition is met using R_NZCV register in self.cd.arch_dbg.state.R_NZCV
            if not self.cd.arch_dbg.state.NZCV & 0b0010:
                return target
        elif c_insn_decoded.mnemonic == "b.hi":
            target = c_insn_decoded.operands[0].value.imm
            # Check if condition is met using R_NZCV register in self.cd.arch_dbg.state.R_NZCV
            if self.cd.arch_dbg.state.NZCV & 0b1100:
                return target
        elif c_insn_decoded.mnemonic == "b.ls":
            target = c_insn_decoded.operands[0].value.imm
            # Check if condition is met using R_NZCV register in self.cd.arch_dbg.state.R_NZCV
            if not self.cd.arch_dbg.state.NZCV & 0b1100:
                return target
        elif c_insn_decoded.mnemonic == "b.ge":
            target = c_insn_decoded.operands[0].value.imm
            # Check if condition is met using R_NZCV register in self.cd.arch_dbg.state.R_NZCV
            if self.cd.arch_dbg.state.NZCV & 0b1001:
                return target
        elif c_insn_decoded.mnemonic == "b.lt":
            target = c_insn_decoded.operands[0].value.imm
            # Check if condition is met using R_NZCV register in self.cd.arch_dbg.state.R_NZCV
            if not self.cd.arch_dbg.state.NZCV & 0b1001:
                return target
        elif c_insn_decoded.mnemonic == "b.gt":
            target = c_insn_decoded.operands[0].value.imm
            # Check if condition is met using R_NZCV register in self.cd.arch_dbg.state.R_NZCV
            if self.cd.arch_dbg.state.NZCV & 0b0111:
                return target
        elif c_insn_decoded.mnemonic == "b.le":
            target = c_insn_decoded.operands[0].value.imm
            # Check if condition is met using R_NZCV register in self.cd.arch_dbg.state.R_NZCV
            if not self.cd.arch_dbg.state.NZCV & 0b0111:
                return target
        elif c_insn_decoded.mnemonic == "b.al":
            target = c_insn_decoded.operands[0].value.imm
            return target
        elif c_insn_decoded.mnemonic == "ret":
            # Get target register
            target = c_insn_decoded.operands[0].value.reg
            return self.cd.arch_dbg.state.get_reg(target)
        elif c_insn_decoded.mnemonic == "br" or c_insn_decoded.mnemonic == "blr":
            # Get target register
            target = c_insn_decoded.operands[0].value.reg
            return self.cd.arch_dbg.state.get_reg(target)
        return self.pc + INSTRUCTION_SIZE
        
    def step(self):
        c_insn = self.cd.memdump_region(self.pc, 4)
        
        next_address = self.get_next_addr()
        next_block = self.cd.memdump_region(next_address, 0x10)
        
        # Decode instruction 
        instr_decoded =  self.sc.disasm_bytes(c_insn, self.pc)
        
        # TODO predict the next instruction, even if it is a conditional branch
        self._shadow_pc = next_address
        
        # Place the debugger hook at pc + INSTRUCTION_SIZE
        self.cd.memwrite_region(next_address, self.cd.arch_dbg.sc.branch_absolute(self.cd.arch_dbg.debugger_addr))
        self.cd.restore_stack_and_jump(self.pc)
        assert self.cd.read(4) == b"GiAs", "Stepping failed to return to debugger!"
        
        # Update PC and restore overwritten code
        self.pc = next_address
        self.cd.memwrite_region(self.pc, next_block)
        
        print(instr_decoded)
        pass
    
    def run(self, start):
        self.pc = start
        # TODO figure out when to stop, for example when a function has returned
        while True:
            self.step()
        pass