import struct

from ....concrete_device import *
from .arm64_stepper import *
from ...utils import warn

LIST_ARM64_EXCEPTION_INSTRUCTIONS = ["smc", "svc", "hvc", "brk", "hlt", "dcps1", "dcps2", "dcps3"]


class ARM64ExceptionStepper(ARM64Stepper):
    def __init__(self, cd : ConcreteDevice, pc, debug=False, auto_flush=False, original_vbar=None, debugger_vbar=None, use_breakpoint_stepping=False, use_backend_vbar_sync=False) -> None:
        super().__init__(cd, pc, debug=debug, auto_flush=auto_flush)
        self.original_vbar = original_vbar
        self.debugger_vbar = debugger_vbar if debugger_vbar is not None else self.cd.arch_dbg.vector_table_addr
        self.use_breakpoint_stepping = use_breakpoint_stepping
        self.use_backend_vbar_sync = use_backend_vbar_sync

    def get_active_vbar_name(self):
        current_el = self.cd.arch_dbg.state.R_CURRENT_EL.get_exception_level()
        if current_el == 3:
            return "VBAR_EL3"
        if current_el == 2:
            return "VBAR_EL2"
        if current_el == 1:
            return "VBAR_EL1"
        raise RuntimeError("ARM64ExceptionStepper only supports EL1/EL2/EL3 stepping")

    def get_active_elr_name(self):
        current_el = self.cd.arch_dbg.state.R_CURRENT_EL.get_exception_level()
        if current_el == 3:
            return "ELR_EL3"
        if current_el == 2:
            return "ELR_EL2"
        if current_el == 1:
            return "ELR_EL1"
        raise RuntimeError("ARM64ExceptionStepper only supports EL1/EL2/EL3 stepping")

    def get_original_vbar(self):
        if self.original_vbar is not None:
            return self.original_vbar

        if hasattr(self.cd.arch_dbg, "vbar_el3_original") and self.cd.arch_dbg.vbar_el3_original:
            return self.cd.arch_dbg.vbar_el3_original

        return getattr(self.cd.arch_dbg.state, self.get_active_vbar_name())

    def write_debugger_vbar(self):
        if not hasattr(self.cd.arch_dbg, "create_debugger_vbar"):
            raise RuntimeError("ARM64ExceptionStepper requires create_debugger_vbar support to install the debugger VBAR")

        debugger_vbar = self.cd.arch_dbg.create_debugger_vbar()
        debugger_vbar_addr = self.debugger_vbar
        self.cd.memwrite_region(debugger_vbar_addr, debugger_vbar)
        return debugger_vbar_addr

    def run_scratch_blob(self, blob, failure_message):
        scratch_addr = self.get_displaced_step_addr()
        original_blob = self.cd.memdump_region(scratch_addr, len(blob))
        self.cd.memwrite_region(scratch_addr, blob)
        try:
            if self.auto_flush:
                self.cd.write(b"FLSH")
            self.cd.restore_stack_and_jump(scratch_addr)
            assert self.cd.read(4) == b"GiAs", failure_message
        finally:
            self.cd.memwrite_region(scratch_addr, original_blob)

    def build_direct_vbar_exception_blob(self, c_insn, debugger_vbar_addr):
        vbar_name = self.get_active_vbar_name()
        elr_name = self.get_active_elr_name()
        shell = f"""
            sub sp, sp, #16
            str x15, [sp]
            str x16, [sp, #8]
            ldr x15, VBAR_addr
            msr {vbar_name}, x15
            isb
            ldr x15, TARGET_addr
            msr {elr_name}, x15
            ldr x16, [sp, #8]
            ldr x15, [sp]
            add sp, sp, #16
            eret
            TARGET_addr: .quad {hex(self.pc)}
            VBAR_addr: .quad {hex(debugger_vbar_addr)}
        """
        return self.cd.arch_dbg.ks.asm(shell, as_bytes=True)[0]

    def build_direct_vbar_restore_blob(self, vbar_addr):
        vbar_name = self.get_active_vbar_name()
        shell = f"""
            sub sp, sp, #16
            str x16, [sp]
            ldr x16, VBAR_addr
            msr {vbar_name}, x16
            isb
            ldr x16, [sp]
            add sp, sp, #16
            ldr x15, DEBUGGER_addr
            br x15
            DEBUGGER_addr: .quad {hex(self.cd.arch_dbg.debugger_addr)}
            VBAR_addr: .quad {hex(vbar_addr)}
        """
        return self.cd.arch_dbg.ks.asm(shell, as_bytes=True)[0]

    def restore_original_vbar_direct(self, original_vbar):
        setattr(self.cd.arch_dbg.state, self.get_active_vbar_name(), original_vbar)
        restore_blob = self.build_direct_vbar_restore_blob(original_vbar)
        self.run_scratch_blob(restore_blob, "Failed to restore original VBAR via scratch trampoline!")

    def step_exception_instruction_direct_vbar(self, c_insn, c_insn_decoded):
        original_vbar = self.get_original_vbar()
        debugger_vbar_addr = self.write_debugger_vbar()
        exception_blob = self.build_direct_vbar_exception_blob(c_insn, debugger_vbar_addr)

        try:
            self.run_scratch_blob(exception_blob, "Exception stepping failed to return to debugger!")
        finally:
            self.restore_original_vbar_direct(original_vbar)

        self.pc += INSTRUCTION_SIZE

        if self.debug:
            warn(
                "ARM64ExceptionStepper trapped a synchronous exception via a scratch VBAR swap: "
                f"mnemonic={c_insn_decoded.mnemonic}, next_pc={self.pc:#x}"
            )

    def install_debugger_vbar(self):
        if not hasattr(self.cd.arch_dbg, "sync_special_regs"):
            raise RuntimeError("ARM64ExceptionStepper requires sync_special_regs support to swap the active VBAR")

        original_vbar = self.get_original_vbar()
        debugger_vbar_addr = self.write_debugger_vbar()
        setattr(self.cd.arch_dbg.state, self.get_active_vbar_name(), debugger_vbar_addr)
        try:
            self.cd.arch_dbg.sync_special_regs()
        except Exception as exc:
            setattr(self.cd.arch_dbg.state, self.get_active_vbar_name(), original_vbar)
            raise RuntimeError("ARM64ExceptionStepper failed to sync the debugger VBAR into the target backend") from exc
        return original_vbar

    def restore_original_vbar(self, original_vbar):
        setattr(self.cd.arch_dbg.state, self.get_active_vbar_name(), original_vbar)
        try:
            self.cd.arch_dbg.sync_special_regs()
        except Exception:
            self.restore_original_vbar_direct(original_vbar)

    def step_exception_instruction(self, c_insn, c_insn_decoded):
        if not self.use_backend_vbar_sync:
            self.step_exception_instruction_direct_vbar(c_insn, c_insn_decoded)
            return

        try:
            original_vbar = self.install_debugger_vbar()
        except RuntimeError:
            self.step_exception_instruction_direct_vbar(c_insn, c_insn_decoded)
            return

        try:
            self.cd.restore_stack_and_jump(self.pc)
            assert self.cd.read(4) == b"GiAs", "Exception stepping failed to return to debugger!"
        finally:
            self.restore_original_vbar(original_vbar)

        # For synchronous exception-generating instructions the architectural resume
        # point is the next instruction, even though we stopped by hijacking the VBAR.
        self.pc += INSTRUCTION_SIZE

        if self.debug:
            warn(
                "ARM64ExceptionStepper trapped a synchronous exception via the debugger VBAR: "
                f"mnemonic={c_insn_decoded.mnemonic}, next_pc={self.pc:#x}"
            )

    def get_patch_targets(self, c_insn_decoded, next_address):
        targets = [next_address]
        fallthrough = self.pc + INSTRUCTION_SIZE

        if c_insn_decoded.mnemonic in LIST_ARM64_BRANCH_CONDITIONAL:
            branch_target = c_insn_decoded.operands[0].value.imm
            for target in (branch_target, fallthrough):
                if target not in targets:
                    targets.append(target)
            return targets

        if c_insn_decoded.mnemonic in ["cbz", "cbnz"]:
            branch_target = c_insn_decoded.operands[1].value.imm
            for target in (branch_target, fallthrough):
                if target not in targets:
                    targets.append(target)

        return targets

    def step(self):
        c_insn = self.cd.memdump_region(self.pc, 4)
        c_insn_decoded = next(self.sc.cs.disasm(c_insn, self.pc))

        self.cd.fetch_special_regs()
        if c_insn_decoded.mnemonic in LIST_ARM64_EXCEPTION_INSTRUCTIONS:
            self.step_exception_instruction(c_insn, c_insn_decoded)
            return

        if not self.use_breakpoint_stepping:
            super().step()
            return

        next_address = self.get_next_addr()
        if next_address == self.pc:
            warn(
                "ARM64ExceptionStepper cannot place a BRK on the current instruction address for a self-loop branch. "
                "Use ARM64Stepper displaced stepping for this path."
            )
            self.step_displaced(c_insn, c_insn_decoded, next_address)
            return

        try:
            original_vbar = self.install_debugger_vbar()
        except RuntimeError:
            warn(
                "ARM64ExceptionStepper could not sync the debugger VBAR into the target backend. "
                "Falling back to ARM64Stepper hook-based stepping for this instruction."
            )
            super().step()
            return

        patched = []
        targets = self.get_patch_targets(c_insn_decoded, next_address)

        for address in targets:
            if address == self.pc:
                continue
            original = self.cd.memdump_region(address, len(self.sc.brk_ins))
            self.cd.memwrite_region(address, self.sc.brk_ins)
            patched.append((address, original))

        try:
            if self.auto_flush:
                self.cd.write(b"FLSH")
            self.cd.restore_stack_and_jump(self.pc)
            assert self.cd.read(4) == b"GiAs", "Exception stepping failed to return to debugger!"
        finally:
            try:
                for address, original in patched:
                    self.cd.memwrite_region(address, original)
            finally:
                self.restore_original_vbar(original_vbar)

        self.pc = next_address