from ....concrete_device import *
from .asm_arm64 import *
from ...utils import warn

INSTRUCTION_SIZE = 4
ABSOLUTE_HOOK_PATCH_SIZE = 16
DISPLACED_STEP_SCRATCH_DELTA = 0x400
LIST_ARM64_BRANCH_INSTRUCTIONS = ["b", "bl", "b.eq", "b.ne", "b.hs", "b.cs", "b.lo", "b.cc", "b.mi", "b.pl", "b.vs", "b.vc", "b.hi", "b.ls", "b.ge", "b.lt", "b.gt", "b.le", "b.al", "ret", "br", "blr", "cbz", "cbnz"]
LIST_ARM64_BRANCH_WITH_LINK = ["bl", "blr"]
LIST_ARM64_BRANCH_CONDITIONAL = ["b.eq", "b.ne", "b.hs", "b.cs", "b.lo", "b.cc", "b.mi", "b.pl", "b.vs", "b.vc", "b.hi", "b.ls", "b.ge", "b.lt", "b.gt", "b.le"]


class ARM64Stepper:
    def __init__(self, cd : ConcreteDevice , pc, debug=False, auto_flush=False) -> None:
        self.cd = cd
        self.sc : ShellcodeCrafter = self.cd.arch_dbg.sc
        self.pc = pc
        self.debug = debug
        self.auto_flush = auto_flush
        self.saved_pcs = {}
        self.sc.cs.detail = True #https://github.com/capstone-engine/capstone/issues/1275

        self.hook_type = "ldr_branch_0x10"

        self.breakpoints = {}
        self.jump_over = {}

    def get_displaced_step_addr(self):
        if hasattr(self.cd, "ga_stack_location"):
            return self.cd.ga_stack_location + DISPLACED_STEP_SCRATCH_DELTA
        return self.cd.arch_dbg.storage_addr + DISPLACED_STEP_SCRATCH_DELTA

    def build_displaced_step_blob(self, c_insn, c_insn_decoded) -> bytes:
        # The overlap case only happens for control-flow that re-enters the patch window.
        # Recreate the side effects we need from scratch memory and stop in the debugger
        # without modifying the live branch target in place.
        if c_insn_decoded.mnemonic in LIST_ARM64_BRANCH_WITH_LINK:
            shell = f"""
                ldr x15, LR_addr
                mov x30, x15
                ldr x15, DEBUGGER_addr
                br x15
                LR_addr: .quad {hex(self.pc + INSTRUCTION_SIZE)}
                DEBUGGER_addr: .quad {hex(self.cd.arch_dbg.debugger_addr)}
            """
            return self.cd.arch_dbg.ks.asm(shell, as_bytes=True)[0]

        if c_insn_decoded.mnemonic in LIST_ARM64_BRANCH_INSTRUCTIONS:
            return self.cd.arch_dbg.sc.branch_absolute(self.cd.arch_dbg.debugger_addr)

        return c_insn + self.cd.arch_dbg.sc.branch_absolute(self.cd.arch_dbg.debugger_addr)

    def step_displaced(self, c_insn, c_insn_decoded, next_address):
        displaced_addr = self.get_displaced_step_addr()
        displaced_blob = self.build_displaced_step_blob(c_insn, c_insn_decoded)
        displaced_original = self.cd.memdump_region(displaced_addr, len(displaced_blob))

        self.cd.memwrite_region(displaced_addr, displaced_blob)
        if self.auto_flush:
            self.cd.write(b"FLSH")
        self.cd.restore_stack_and_jump(displaced_addr)
        assert self.cd.read(4) == b"GiAs", "Displaced stepping failed to return to debugger!"

        self.pc = next_address
        self.cd.memwrite_region(displaced_addr, displaced_original)

    def get_next_addr(self) -> int:
        c_insn = self.cd.memdump_region(self.pc, 4)
        c_insn_decoded = next(self.sc.cs.disasm(c_insn, self.pc))
        if c_insn_decoded.mnemonic in LIST_ARM64_BRANCH_INSTRUCTIONS:
            # It is a branch instruction
            next_addr = self.get_branch_addr(c_insn_decoded)
        else:
            next_addr = self.pc + INSTRUCTION_SIZE

        if next_addr in self.jump_over:
            target = self.jump_over[next_addr]
            if type(target) == str:
                target = getattr(self.cd.arch_dbg.state, target)
            else:
                assert type(target) == int, "jump_over target must be int or str"

            if self.debug:
                print(f"Jumping over from {hex(next_addr)} to {hex(target)}")
            next_addr = target
        return next_addr

    def get_branch_addr(self, c_insn_decoded) -> int:
        # Check if it is a branch instruction
        if c_insn_decoded.mnemonic == "b":
            return int(c_insn_decoded.op_str[3:], 16)
        elif c_insn_decoded.mnemonic == "bl":
            return int(c_insn_decoded.op_str[3:], 16)

        # For conditional branches, get current NZCV flags

        nzcv = self.cd.arch_dbg.state.R_NZCV
        # Handle conditional branches with proper condition evaluation
        if c_insn_decoded.mnemonic == "b.eq":
            target = c_insn_decoded.operands[0].value.imm
            if nzcv.condition_met("eq"):
                return int(c_insn_decoded.op_str[3:], 16)
        elif c_insn_decoded.mnemonic == "b.ne":
            target = c_insn_decoded.operands[0].value.imm
            if nzcv.condition_met("ne"):
                return int(c_insn_decoded.op_str[3:], 16)
        elif c_insn_decoded.mnemonic == "b.hs" or c_insn_decoded.mnemonic == "b.cs":
            target = c_insn_decoded.operands[0].value.imm
            if nzcv.condition_met("hs"):
                return int(c_insn_decoded.op_str[3:], 16)
        elif c_insn_decoded.mnemonic == "b.lo" or c_insn_decoded.mnemonic == "b.cc":
            target = c_insn_decoded.operands[0].value.imm
            if nzcv.condition_met("lo"):
                return int(c_insn_decoded.op_str[3:], 16)
        elif c_insn_decoded.mnemonic == "b.mi":
            target = c_insn_decoded.operands[0].value.imm
            if nzcv.condition_met("mi"):
                return int(c_insn_decoded.op_str[3:], 16)
        elif c_insn_decoded.mnemonic == "b.pl":
            target = c_insn_decoded.operands[0].value.imm
            if nzcv.condition_met("pl"):
                return int(c_insn_decoded.op_str[3:], 16)
        elif c_insn_decoded.mnemonic == "b.vs":
            target = c_insn_decoded.operands[0].value.imm
            if nzcv.condition_met("vs"):
                return int(c_insn_decoded.op_str[3:], 16)
        elif c_insn_decoded.mnemonic == "b.vc":
            target = c_insn_decoded.operands[0].value.imm
            if nzcv.condition_met("vc"):
                return int(c_insn_decoded.op_str[3:], 16)
        elif c_insn_decoded.mnemonic == "b.hi":
            target = c_insn_decoded.operands[0].value.imm
            if nzcv.condition_met("hi"):
                return int(c_insn_decoded.op_str[3:], 16)
        elif c_insn_decoded.mnemonic == "b.ls":
            target = c_insn_decoded.operands[0].value.imm
            if nzcv.condition_met("ls"):
                return int(c_insn_decoded.op_str[3:], 16)
        elif c_insn_decoded.mnemonic == "b.ge":
            target = c_insn_decoded.operands[0].value.imm
            if nzcv.condition_met("ge"):
                return int(c_insn_decoded.op_str[3:], 16)
        elif c_insn_decoded.mnemonic == "b.lt":
            target = c_insn_decoded.operands[0].value.imm
            if nzcv.condition_met("lt"):
                return int(c_insn_decoded.op_str[3:], 16)
        elif c_insn_decoded.mnemonic == "b.gt":
            target = c_insn_decoded.operands[0].value.imm
            if nzcv.condition_met("gt"):
                return int(c_insn_decoded.op_str[3:], 16)
        elif c_insn_decoded.mnemonic == "b.le":
            target = c_insn_decoded.operands[0].value.imm
            if nzcv.condition_met("le"):
                return int(c_insn_decoded.op_str[3:], 16)
        elif c_insn_decoded.mnemonic == "b.al":
            target = c_insn_decoded.operands[0].value.imm
            return int(c_insn_decoded.op_str[3:], 16)
        elif c_insn_decoded.mnemonic == "cbz":
            # Compare and Branch on Zero: branch if register is zero
            reg = c_insn_decoded.operands[0].value.reg
            target = int(c_insn_decoded.op_str.split(", ")[1][3:], 16)
            reg_value = getattr(self.cd.arch_dbg.state, self.sc.cs.reg_name(reg).upper())
            if reg_value == 0:
                return target
        elif c_insn_decoded.mnemonic == "cbnz":
            # Compare and Branch on Non-Zero: branch if register is not zero
            reg = c_insn_decoded.operands[0].value.reg
            target = int(c_insn_decoded.op_str.split(", ")[1][3:], 16)
            reg_value = getattr(self.cd.arch_dbg.state, self.sc.cs.reg_name(reg).upper())
            if reg_value != 0:
                return target
        elif c_insn_decoded.mnemonic == "ret":
            # Get target register, default to x30 (LR) if no operand
            if len(c_insn_decoded.operands) > 0:
                target = c_insn_decoded.operands[0].value.reg
                return getattr(self.cd.arch_dbg.state, self.sc.cs.reg_name(target).upper())
            else:
                return getattr(self.cd.arch_dbg.state, "X30")
        elif c_insn_decoded.mnemonic == "br" or c_insn_decoded.mnemonic == "blr":
            # Get target register
            target = c_insn_decoded.operands[0].value.reg
            return getattr(self.cd.arch_dbg.state, self.sc.cs.reg_name(target).upper())
        else:
            raise Exception(f"Branch instruction {c_insn_decoded.mnemonic} not implemented")

        # Fall through case - condition not met, continue to next instruction
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
        hook_blob = self.cd.arch_dbg.sc.branch_absolute(self.cd.arch_dbg.debugger_addr)
        hook_size = len(hook_blob) or ABSOLUTE_HOOK_PATCH_SIZE
        next_block = self.cd.memdump_region(hook_addr, hook_size)

        if self.debug:
            print(f"Hook at {hex(hook_addr)}")
            self.cd.arch_dbg.state.print_ctx()

        # Write hook to the next block
        self.cd.fetch_special_regs()
        self.cd.memwrite_region(hook_addr, hook_blob)
        self.cd.write(b"FLSH")
        self.cd.restore_stack_and_jump(self.pc)
        assert self.cd.read(4) == b"GiAs", "Stepping failed to return to debugger!"

        # Update PC and restore overwritten code
        self.pc = hook_addr
        self.cd.memwrite_region(hook_addr, next_block) # restore code
        if self.debug:
            print(f"Block at {hex(hook_addr)}")

    def step(self):
        c_insn = self.cd.memdump_region(self.pc, 4)
        c_insn_decoded = next(self.sc.cs.disasm(c_insn, self.pc))

        next_address = self.get_next_addr()
        hook_blob = self.cd.arch_dbg.sc.branch_absolute(self.cd.arch_dbg.debugger_addr)
        hook_size = len(hook_blob) or ABSOLUTE_HOOK_PATCH_SIZE
        next_block = self.cd.memdump_region(next_address, hook_size)

        # Decode instruction
        instr_decoded =  self.sc.disasm_bytes(c_insn, self.pc)

        # TODO predict the next instruction, even if it is a conditional branch
        self._shadow_pc = next_address

        self.cd.fetch_special_regs()
        if self.debug:
            print("===================================")
            print(f"PC: {hex(self.pc)}")
            print(f"Next PC: {hex(next_address)}")
            print(f"Next block: {next_block}")
            print( "NZCV:", bin(self.cd.arch_dbg.state.NZCV))
            print(f"Instruction: {instr_decoded}")
            print(self.cd.arch_dbg.state.get_ctx())

        # Place the debugger hook at pc + INSTRUCTION_SIZE
        if next_address < self.pc + INSTRUCTION_SIZE and self.pc < next_address + hook_size:
            warn(
                "ARM64Stepper temporary hook overlaps the current instruction: "
                f"pc={self.pc:#x}, hook=[{next_address:#x}, {next_address + hook_size:#x}). "
                "Falling back to displaced stepping from scratch memory."
            )
            self.step_displaced(c_insn, c_insn_decoded, next_address)
            return
        self.cd.memwrite_region(next_address, hook_blob)
        if self.auto_flush:
            self.cd.write(b"FLSH") # TODO TODO add optional cache flush
        self.cd.restore_stack_and_jump(self.pc)
        assert self.cd.read(4) == b"GiAs", "Stepping failed to return to debugger!"

        # Update PC and restore overwritten code
        self.pc = next_address
        self.cd.memwrite_region(self.pc, next_block)

        if self.debug:
            print(instr_decoded)

    def run(self, start, end=None):
        self.pc = start
        # TODO figure out when to stop, for example when a function has returned
        while self.pc != end if end is not None else True:
            self.step()