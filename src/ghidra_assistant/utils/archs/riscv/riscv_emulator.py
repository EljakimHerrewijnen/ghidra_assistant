from __future__ import annotations

from ...emulator.base_emulator import BaseEmulator

# ABI register names (lowercase) for convenience access via __getattr__/__setattr__
_RISCV_KNOWN_REGS: frozenset[str] = frozenset(
    {f"X{i}" for i in range(32)}
    | {
        "ZERO", "RA", "SP", "GP", "TP",
        "T0", "T1", "T2",
        "S0", "FP", "S1",
        "A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7",
        "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10", "S11",
        "T3", "T4", "T5", "T6",
        "PC",
    }
)


class RiscvEmulator(BaseEmulator):
    """RISC-V emulator built on top of BaseEmulator.

    *bits* selects 32- or 64-bit mode (default: 64).  Uses the unicorn
    backend by default::

        emu = RiscvEmulator()          # RV64
        emu = RiscvEmulator(bits=32)   # RV32

    Register access works via ABI names or Xn notation::

        emu.a0 = 0x1234
        emu.get_register("X10")  # same register
    """

    def __init__(self, bits: int = 64, backend: str = "unicorn", **kwargs) -> None:
        if bits not in (32, 64):
            raise ValueError(f"bits must be 32 or 64, got {bits}")
        self._bits = bits
        arch = "riscv32" if bits == 32 else "riscv64"
        super().__init__(arch, "riscv", backend=backend, **kwargs)
        self._setup_disasm()

    def _setup_disasm(self) -> None:
        try:
            from capstone import Cs, CS_ARCH_RISCV
            from capstone import CS_MODE_RISCV32, CS_MODE_RISCV64
            cs_mode = CS_MODE_RISCV32 if self._bits == 32 else CS_MODE_RISCV64
            self.md = Cs(CS_ARCH_RISCV, cs_mode)
            self.md.detail = True
            self.cs = self.md
        except (ImportError, AttributeError):
            self.md = None
            self.cs = None

    # ------- register attribute interface -------

    def __getattr__(self, name: str):
        upper = name.upper()
        if upper in _RISCV_KNOWN_REGS:
            return self.get_register(upper)
        return super().__getattr__(name)

    def __setattr__(self, name: str, value) -> None:
        upper = name.upper()
        if upper in _RISCV_KNOWN_REGS:
            self.set_register(upper, value)
        else:
            object.__setattr__(self, name, value)

    # ------- helpers -------

    def get_registers(self) -> list[int]:
        return [self.get_register(f"X{i}") for i in range(32)] + [self.get_register("PC")]

    def disasm(self, address: int | None = None, dlen: int = 0x80) -> list:
        if self.md is None:
            raise RuntimeError("capstone RISC-V disassembly not available")
        if address is None:
            address = self.get_register("PC")
        data = self.mem_read(address, dlen)
        return list(self.md.disasm(data, address))

    def get_mapping(self, address: int):
        for region in self.mem_regions():
            if region[0] <= address < region[1]:
                return region
        return None

    def is_mapped(self, address: int) -> bool:
        return self.get_mapping(address) is not None
