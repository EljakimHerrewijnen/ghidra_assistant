from __future__ import annotations

from ...emulator.base_emulator import BaseEmulator

_X86_64_KNOWN_REGS: frozenset[str] = frozenset({
    "RAX", "RBX", "RCX", "RDX", "RSI", "RDI", "RBP", "RSP",
    "R8", "R9", "R10", "R11", "R12", "R13", "R14", "R15",
    "RIP", "RFLAGS",
    "EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP", "EIP",
    "AX", "BX", "CX", "DX", "SI", "DI", "BP", "SP",
    "CS", "DS", "ES", "FS", "GS", "SS",
    "EFLAGS",
    "PC", "FP",
})

_X86_32_KNOWN_REGS: frozenset[str] = frozenset({
    "EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP", "EIP",
    "AX", "BX", "CX", "DX", "SI", "DI", "BP", "SP",
    "CS", "DS", "ES", "FS", "GS", "SS",
    "EFLAGS",
    "PC", "FP",
})


class X86Emulator(BaseEmulator):
    """x86 / x86-64 emulator built on top of BaseEmulator.

    *bits* selects 32- or 64-bit mode (default: 64).  Uses the unicorn
    backend by default::

        emu = X86Emulator()         # 64-bit
        emu = X86Emulator(bits=32)  # 32-bit

    Register access works via attribute syntax::

        emu.rax = 0xDEADBEEF
        emu.RIP            # same as get_register("RIP")
    """

    def __init__(self, bits: int = 64, backend: str = "unicorn", **kwargs) -> None:
        if bits not in (32, 64):
            raise ValueError(f"bits must be 32 or 64, got {bits}")
        self._bits = bits
        self._known_regs = _X86_64_KNOWN_REGS if bits == 64 else _X86_32_KNOWN_REGS
        arch = "x86_64" if bits == 64 else "x86"
        mode = "64" if bits == 64 else "32"
        super().__init__(arch, mode, backend=backend, **kwargs)
        self._setup_disasm()

    def _setup_disasm(self) -> None:
        try:
            from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_MODE_64
            cs_mode = CS_MODE_64 if self._bits == 64 else CS_MODE_32
            self.md = Cs(CS_ARCH_X86, cs_mode)
            self.md.detail = True
        except ImportError:
            self.md = None

    # ------- register attribute interface -------

    def __getattr__(self, name: str):
        upper = name.upper()
        if upper in self._known_regs:
            return self.get_register(upper)
        return super().__getattr__(name)

    def __setattr__(self, name: str, value) -> None:
        # _known_regs may not exist yet during __init__ super() call
        known = object.__getattribute__(self, "_known_regs") if "_known_regs" in self.__dict__ else frozenset()
        upper = name.upper()
        if upper in known:
            self.set_register(upper, value)
        else:
            object.__setattr__(self, name, value)

    # ------- helpers -------

    @property
    def pc_reg(self) -> str:
        return "RIP" if self._bits == 64 else "EIP"

    def get_registers(self) -> dict[str, int]:
        if self._bits == 64:
            names = [
                "RAX", "RBX", "RCX", "RDX", "RSI", "RDI", "RBP", "RSP",
                "R8", "R9", "R10", "R11", "R12", "R13", "R14", "R15", "RIP",
            ]
        else:
            names = ["EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP", "EIP"]
        ctx: dict[str, int] = {}
        for n in names:
            try:
                ctx[n] = self.get_register(n)
            except Exception:
                continue
        return ctx

    def disasm(self, address: int | None = None, dlen: int = 0x40) -> list:
        if self.md is None:
            raise RuntimeError("capstone x86 disassembly not available")
        if address is None:
            address = self.get_register(self.pc_reg)
        data = self.mem_read(address, dlen)
        return list(self.md.disasm(data, address))

    def get_mapping(self, address: int):
        for region in self.mem_regions():
            if region[0] <= address < region[1]:
                return region
        return None

    def is_mapped(self, address: int) -> bool:
        return self.get_mapping(address) is not None
