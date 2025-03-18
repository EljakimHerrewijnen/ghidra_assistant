from ....concrete_device import *
from .asm_arm64 import *

INSTRUCTION_SIZE = 4
LIST_ARM64_BRANCH_INSTRUCTIONS = ["b", "bl", "b.eq", "b.ne", "b.hs", "b.lo", "b.mi", "b.pl", "b.vs", "b.vc", "b.hi", "b.ls", "b.ge", "b.lt", "b.gt", "b.le", "b.al", "ret", "br", "blr"]
LIST_ARM64_BRANCH_WITH_LINK = ["bl", "blr"]
LIST_ARM64_BRANCH_CONDITIONAL = ["b.eq", "b.ne", "b.hs", "b.lo", "b.mi", "b.pl", "b.vs", "b.vc", "b.hi", "b.ls", "b.ge", "b.lt", "b.gt", "b.le"]


class ARM64Stepper:
    def __init__(self, cd : ConcreteDevice , pc, debug=False) -> None:
        self.cd = cd
        self.sc : ShellcodeCrafter = self.cd.arch_dbg.sc
        self.pc = pc
        self.debug = debug
        self.saved_pcs = {}
        self.sc.cs.detail = True #https://github.com/capstone-engine/capstone/issues/1275

        self.hook_type = "ldr_branch_0x10"

    def get_next_addr(self) -> int:
        c_insn = self.cd.memdump_region(self.pc, 4)
        c_insn_decoded = next(self.sc.cs.disasm(c_insn, self.pc))
        if c_insn_decoded.mnemonic in LIST_ARM64_BRANCH_INSTRUCTIONS:
            return self.get_branch_addr(c_insn_decoded)
        else:
            return self.pc + INSTRUCTION_SIZE

    def get_branch_addr(self, c_insn_decoded) -> int:
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
        else:
            raise Exception(f"Branch instruction {c_insn_decoded.mnemonic} not implemented")
        return c_insn_decoded.address + INSTRUCTION_SIZE

    def get_next_block(self, from_pc) -> int:
        '''
        Keep reading instructions until a branch instruction is found
        '''
        while True:
            c_insn = self.cd.memdump_region(from_pc, 4)
            c_insn_decoded = next(self.sc.cs.disasm(c_insn, from_pc))

            # Check if it is a branch instruction, return the target address
            if c_insn_decoded.mnemonic in LIST_ARM64_BRANCH_INSTRUCTIONS:
                return from_pc

            from_pc += INSTRUCTION_SIZE

    def step_block(self):
        hook_addr = self.get_next_block(self.get_next_addr())
        next_block = self.cd.memdump_region(hook_addr, 0x10)

        if self.debug:
            print(f"Hook at {hex(hook_addr)}")
            self.cd.arch_dbg.state.print_ctx()

        # Write hook to the next block
        self.cd.fetch_special_regs()
        self.cd.memwrite_region(hook_addr, self.sc.branch_absolute(self.cd.arch_dbg.debugger_addr))
        self.cd.write(b"FLSH")
        self.cd.restore_stack_and_jump(self.pc)
        assert self.cd.read(4) == b"GiAs", "Stepping failed to return to debugger!"

        # Update PC and restore overwritten code
        self.pc = hook_addr
        self.cd.memwrite_region(hook_addr, next_block) # restore code
        print(f"Block at {hex(hook_addr)}")

    def step(self):
        c_insn = self.cd.memdump_region(self.pc, 4)

        next_address = self.get_next_addr()
        next_block = self.cd.memdump_region(next_address, 0x10)

        # Decode instruction
        instr_decoded =  self.sc.disasm_bytes(c_insn, self.pc)

        # TODO predict the next instruction, even if it is a conditional branch
        self._shadow_pc = next_address

        self.cd.fetch_special_regs()
        if self.debug:
            print(f"PC: {hex(self.pc)}")
            print(f"Next PC: {hex(next_address)}")
            print(f"Next block: {next_block}")
            print(f"Instruction: {instr_decoded}")
            self.cd.arch_dbg.state.print_ctx()

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