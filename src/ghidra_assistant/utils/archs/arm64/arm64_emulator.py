from __future__ import annotations

import logging

from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from keystone import Ks, KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN

from ..asm_utils import ShellcodeCrafter
from ...utils import info, p32, p8
from ....concrete_device import ConcreteDevice
from ...emulator.base_emulator import BaseEmulator

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Set of register names whose read/write is routed through get/set_register.
# __getattr__/__setattr__ normalise to uppercase before lookup so lowercase
# aliases (e.g. "pc") work transparently.
# ---------------------------------------------------------------------------
_ARM64_KNOWN_REGS: frozenset[str] = frozenset(
    {f"X{i}" for i in range(31)}
    | {f"W{i}" for i in range(31)}
    | {
        "X29", "X30", "SP", "PC", "LR", "FP",
        "NZCV", "DAIF",
        "VBAR_EL1", "VBAR_EL2", "VBAR_EL3",
        "ELR_EL0", "ELR_EL1", "ELR_EL2", "ELR_EL3",
        "SP_EL0", "SP_EL1", "SP_EL2",
        "SPSR_EL1", "SPSR_EL2", "SPSR_EL3",
        "SCTLR_EL1", "SCTLR_EL2", "SCTLR_EL3",
        "TTBR0_EL1", "TTBR0_EL2", "TTBR0_EL3",
        "TTBR1_EL1",
        "TCR_EL1", "TCR_EL2", "TCR_EL3",
        "MAIR_EL1", "MAIR_EL2", "MAIR_EL3",
        "HCR_EL2", "VTCR_EL2", "VTTBR_EL2",
    }
)


class ARM64Emulator(BaseEmulator):
    """ARM64 emulator built on top of BaseEmulator.

    Uses the unicorn backend by default.  Any backend supported by
    BaseEmulator can be selected via the *backend* keyword argument.

    Register access is available through attribute syntax (both upper- and
    lowercase) as well as the standard ``get_register`` / ``set_register``
    interface::

        emu = ARM64Emulator()
        emu.X0 = 0xDEAD
        emu.pc = 0x1000    # lowercase alias works too
    """

    def __init__(self, backend: str = "unicorn", **kwargs) -> None:
        super().__init__("arm64", "arm", backend=backend, **kwargs)
        self.md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
        self.md.detail = True
        self.cs = self.md
        self.ks = Ks(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN)
        self.setup_shellcode()

    # ------- register attribute interface -------

    def __getattr__(self, name: str):
        upper = name.upper()
        if upper in _ARM64_KNOWN_REGS:
            return self.get_register(upper)
        return super().__getattr__(name)

    def __setattr__(self, name: str, value) -> None:
        upper = name.upper()
        if upper in _ARM64_KNOWN_REGS:
            self.set_register(upper, value)
        else:
            object.__setattr__(self, name, value)

    # ------- helpers -------

    def setup_shellcode(self) -> None:
        self.sc = ShellcodeCrafter(self.cs, self.ks)

    def get_mapping(self, address: int):
        for region in self.mem_regions():
            if region[0] <= address < region[1]:
                return region
        return None

    def is_mapped(self, address: int) -> bool:
        return self.get_mapping(address) is not None

    def get_registers(self) -> list[int]:
        return [self.get_register(f"X{i}") for i in range(31)] + [self.get_register("PC")]

    def disasm(self, address: int | None = None, dlen: int = 0x80) -> list:
        if address is None:
            address = self.get_register("PC")
        data = self.mem_read(address, dlen)
        return list(self.md.disasm(data, address))

    def print_ctx(self, print_f=info) -> None:
        regs = self.get_registers()
        pc = self.get_register("PC")
        sp = self.get_register("SP")
        lr = self.get_register("LR")
        print_f("  x0 : 0x{0:016X}      x1 : 0x{1:016X}      x2 : 0x{2:016X}      x3 : 0x{3:016X}".format(*regs[0:4]))
        print_f("  x4 : 0x{0:016X}      x5 : 0x{1:016X}      x6 : 0x{2:016X}      x7 : 0x{3:016X}".format(*regs[4:8]))
        print_f("  x8 : 0x{0:016X}      x9 : 0x{1:016X}     x10 : 0x{2:016X}     x11 : 0x{3:016X}".format(*regs[8:12]))
        print_f(" x12 : 0x{0:016X}     x13 : 0x{1:016X}     x14 : 0x{2:016X}     x15 : 0x{3:016X}".format(*regs[12:16]))
        print_f(" x16 : 0x{0:016X}     x17 : 0x{1:016X}     x18 : 0x{2:016X}     x19 : 0x{3:016X}".format(*regs[16:20]))
        print_f(" x20 : 0x{0:016X}     x21 : 0x{1:016X}     x22 : 0x{2:016X}     x23 : 0x{3:016X}".format(*regs[20:24]))
        print_f(" x24 : 0x{0:016X}     x25 : 0x{1:016X}     x26 : 0x{2:016X}     x27 : 0x{3:016X}".format(*regs[24:28]))
        print_f(" x28 : 0x{0:016X}     x29 : 0x{1:016X}     x30 : 0x{2:016X}     pc  : 0x{3:016X}".format(*regs[28:32]))
        print_f("  SP : 0x{0:016X}      LR : 0x{1:016X}".format(sp, lr))
        try:
            insn = self.disasm(pc)[0]
            instruction = f"{insn.mnemonic}\t{insn.op_str}"
        except Exception:
            instruction = "???"
        print_f("IP {:016x} :::: {}".format(pc, instruction))

    def install_debugger(self, debugger: ConcreteDevice) -> None:
        self.debugger = debugger

    def hw_itm_handle(self, uc, access, address, size, value, user_data) -> bool:
        """Generic HW-ITM hook: forwards memory accesses to the installed debugger."""
        from unicorn import UC_MEM_WRITE, UC_MEM_READ
        assert hasattr(self, "debugger"), "Debugger not installed!"
        try:
            if access == UC_MEM_WRITE:
                if size == 4:
                    self.debugger.memwrite_region(address, p32(value))
                elif size == 1:
                    self.debugger.memwrite_io(address, p8(value))
                else:
                    raise RuntimeError(f"Unhandled write size {size}")
            elif access == UC_MEM_READ:
                if size == 1:
                    pass
                self.mem_write(address, self.debugger.memdump_region(address, size))
            else:
                raise RuntimeError(f"Unhandled memory access type {access}")
        except Exception as e:
            _log.error(str(e))
            raise
        return True


# Backward-compatible alias so existing code importing ARM64UC_Emulator continues to work.
ARM64UC_Emulator = ARM64Emulator
