from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Register maps: built lazily inside functions to avoid hard import errors
# when unicorn is installed but a specific arch constant file is missing.
# ---------------------------------------------------------------------------

def _build_arm64_reg_map() -> dict[str, int]:
    import unicorn.arm64_const as c
    m: dict[str, int] = {}
    for i in range(31):
        xc = getattr(c, f"UC_ARM64_REG_X{i}", None)
        wc = getattr(c, f"UC_ARM64_REG_W{i}", None)
        if xc is not None:
            m[f"X{i}"] = xc
        if wc is not None:
            m[f"W{i}"] = wc
    _extras = [
        ("SP",        "UC_ARM64_REG_SP"),
        ("PC",        "UC_ARM64_REG_PC"),
        ("LR",        "UC_ARM64_REG_X30"),
        ("FP",        "UC_ARM64_REG_X29"),
        ("X29",       "UC_ARM64_REG_X29"),
        ("X30",       "UC_ARM64_REG_X30"),
        ("NZCV",      "UC_ARM64_REG_NZCV"),
        ("DAIF",      "UC_ARM64_REG_DAIF"),
        ("VBAR_EL1",  "UC_ARM64_REG_VBAR_EL1"),
        ("VBAR_EL2",  "UC_ARM64_REG_VBAR_EL2"),
        ("VBAR_EL3",  "UC_ARM64_REG_VBAR_EL3"),
        ("ELR_EL0",   "UC_ARM64_REG_ELR_EL0"),
        ("ELR_EL1",   "UC_ARM64_REG_ELR_EL1"),
        ("ELR_EL2",   "UC_ARM64_REG_ELR_EL2"),
        ("ELR_EL3",   "UC_ARM64_REG_ELR_EL3"),
        ("SP_EL0",    "UC_ARM64_REG_SP_EL0"),
        ("SP_EL1",    "UC_ARM64_REG_SP_EL1"),
        ("SP_EL2",    "UC_ARM64_REG_SP_EL2"),
        ("SPSR_EL1",  "UC_ARM64_REG_SPSR_EL1"),
        ("SPSR_EL2",  "UC_ARM64_REG_SPSR_EL2"),
        ("SPSR_EL3",  "UC_ARM64_REG_SPSR_EL3"),
        ("SCTLR_EL1", "UC_ARM64_REG_SCTLR_EL1"),
        ("SCTLR_EL2", "UC_ARM64_REG_SCTLR_EL2"),
        ("SCTLR_EL3", "UC_ARM64_REG_SCTLR_EL3"),
        ("TTBR0_EL1", "UC_ARM64_REG_TTBR0_EL1"),
        ("TTBR0_EL2", "UC_ARM64_REG_TTBR0_EL2"),
        ("TTBR0_EL3", "UC_ARM64_REG_TTBR0_EL3"),
        ("TTBR1_EL1", "UC_ARM64_REG_TTBR1_EL1"),
        ("TCR_EL1",   "UC_ARM64_REG_TCR_EL1"),
        ("TCR_EL2",   "UC_ARM64_REG_TCR_EL2"),
        ("TCR_EL3",   "UC_ARM64_REG_TCR_EL3"),
        ("MAIR_EL1",  "UC_ARM64_REG_MAIR_EL1"),
        ("MAIR_EL2",  "UC_ARM64_REG_MAIR_EL2"),
        ("MAIR_EL3",  "UC_ARM64_REG_MAIR_EL3"),
        ("HCR_EL2",   "UC_ARM64_REG_HCR_EL2"),
        ("VTCR_EL2",  "UC_ARM64_REG_VTCR_EL2"),
        ("VTTBR_EL2", "UC_ARM64_REG_VTTBR_EL2"),
    ]
    for name, attr in _extras:
        v = getattr(c, attr, None)
        if v is not None:
            m[name] = v
    return m


def _build_arm_reg_map() -> dict[str, int]:
    import unicorn.arm_const as c
    m: dict[str, int] = {}
    for i in range(16):
        rc = getattr(c, f"UC_ARM_REG_R{i}", None)
        if rc is not None:
            m[f"R{i}"] = rc
            m[f"X{i}"] = rc  # Xn -> Rn alias for compatibility
    _extras = [
        ("SP",   "UC_ARM_REG_SP"),
        ("PC",   "UC_ARM_REG_PC"),
        ("LR",   "UC_ARM_REG_LR"),
        ("FP",   "UC_ARM_REG_R11"),
        ("CPSR", "UC_ARM_REG_CPSR"),
        ("SPSR", "UC_ARM_REG_SPSR"),
    ]
    for name, attr in _extras:
        v = getattr(c, attr, None)
        if v is not None:
            m[name] = v
    return m


def _build_riscv_reg_map() -> dict[str, int]:
    import unicorn.riscv_const as c
    m: dict[str, int] = {}
    for i in range(32):
        rc = getattr(c, f"UC_RISCV_REG_X{i}", None)
        if rc is not None:
            m[f"X{i}"] = rc
    _abi = [
        ("ZERO", 0), ("RA", 1),  ("SP", 2),  ("GP", 3),
        ("TP",   4), ("T0", 5),  ("T1", 6),  ("T2", 7),
        ("S0",   8), ("FP", 8),  ("S1", 9),
        ("A0",  10), ("A1", 11), ("A2", 12), ("A3", 13),
        ("A4",  14), ("A5", 15), ("A6", 16), ("A7", 17),
        ("S2",  18), ("S3", 19), ("S4", 20), ("S5", 21),
        ("S6",  22), ("S7", 23), ("S8", 24), ("S9", 25),
        ("S10", 26), ("S11", 27), ("T3", 28), ("T4", 29),
        ("T5",  30), ("T6", 31),
    ]
    for name, idx in _abi:
        rc = getattr(c, f"UC_RISCV_REG_X{idx}", None)
        if rc is not None:
            m[name] = rc
    pc = getattr(c, "UC_RISCV_REG_PC", None)
    if pc is not None:
        m["PC"] = pc
    return m


def _build_x86_reg_map() -> dict[str, int]:
    import unicorn.x86_const as c
    _regs = [
        # 64-bit GP
        ("RAX", "UC_X86_REG_RAX"), ("RBX", "UC_X86_REG_RBX"),
        ("RCX", "UC_X86_REG_RCX"), ("RDX", "UC_X86_REG_RDX"),
        ("RSI", "UC_X86_REG_RSI"), ("RDI", "UC_X86_REG_RDI"),
        ("RBP", "UC_X86_REG_RBP"), ("RSP", "UC_X86_REG_RSP"),
        ("R8",  "UC_X86_REG_R8"),  ("R9",  "UC_X86_REG_R9"),
        ("R10", "UC_X86_REG_R10"), ("R11", "UC_X86_REG_R11"),
        ("R12", "UC_X86_REG_R12"), ("R13", "UC_X86_REG_R13"),
        ("R14", "UC_X86_REG_R14"), ("R15", "UC_X86_REG_R15"),
        ("RIP", "UC_X86_REG_RIP"),
        # 32-bit GP
        ("EAX", "UC_X86_REG_EAX"), ("EBX", "UC_X86_REG_EBX"),
        ("ECX", "UC_X86_REG_ECX"), ("EDX", "UC_X86_REG_EDX"),
        ("ESI", "UC_X86_REG_ESI"), ("EDI", "UC_X86_REG_EDI"),
        ("EBP", "UC_X86_REG_EBP"), ("ESP", "UC_X86_REG_ESP"),
        ("EIP", "UC_X86_REG_EIP"),
        # 16-bit GP
        ("AX",  "UC_X86_REG_AX"),  ("BX",  "UC_X86_REG_BX"),
        ("CX",  "UC_X86_REG_CX"),  ("DX",  "UC_X86_REG_DX"),
        ("SI",  "UC_X86_REG_SI"),  ("DI",  "UC_X86_REG_DI"),
        ("BP",  "UC_X86_REG_BP"),  ("SP",  "UC_X86_REG_SP"),
        # Segment registers
        ("CS",  "UC_X86_REG_CS"),  ("DS",  "UC_X86_REG_DS"),
        ("ES",  "UC_X86_REG_ES"),  ("FS",  "UC_X86_REG_FS"),
        ("GS",  "UC_X86_REG_GS"),  ("SS",  "UC_X86_REG_SS"),
        # Flags / aliases
        ("EFLAGS", "UC_X86_REG_EFLAGS"),
        ("RFLAGS", "UC_X86_REG_EFLAGS"),
        ("PC",     "UC_X86_REG_RIP"),
        ("FP",     "UC_X86_REG_RBP"),
    ]
    m: dict[str, int] = {}
    for name, attr in _regs:
        v = getattr(c, attr, None)
        if v is not None:
            m[name] = v
    return m


# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------

class UnicornBackend:
    def __init__(self, arch: str, mode: str, init_uc: bool = True) -> None:
        self.arch = arch
        self.mode = mode
        self._uc = None
        self.mem = None
        self._reg_map: dict[str, int] = {}

        if arch == "arm64":
            self._init_arm64(mode, init_uc)
        elif arch == "arm":
            self._init_arm(mode, init_uc)
        elif arch in ("riscv32", "riscv64"):
            self._init_riscv(mode, init_uc, bits=32 if arch == "riscv32" else 64)
        elif arch in ("x86", "x86_64"):
            self._init_x86(mode, init_uc, bits=32 if arch == "x86" else 64)
        else:
            raise ValueError(f"Unsupported arch '{arch}' for unicorn backend")

    # ---- arch initialisers ----

    def _init_arm64(self, mode: str, init_uc: bool) -> None:
        if mode not in ("arm", "aarch64"):
            raise ValueError(f"Unsupported mode '{mode}' for arch 'arm64'")
        from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_LITTLE_ENDIAN
        from ..archs.arm.memory_proxy import MemoryProxy
        if init_uc:
            self._uc = Uc(UC_ARCH_ARM64, UC_MODE_LITTLE_ENDIAN)
            self.mem = MemoryProxy(self._uc)
        self._reg_map = _build_arm64_reg_map()

    def _init_arm(self, mode: str, init_uc: bool) -> None:
        if mode not in ("arm", "thumb"):
            raise ValueError(f"Unsupported mode '{mode}' for arch 'arm'")
        from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_MODE_THUMB
        from ..archs.arm.memory_proxy import MemoryProxy
        if init_uc:
            uc_mode = UC_MODE_THUMB if mode == "thumb" else UC_MODE_ARM
            self._uc = Uc(UC_ARCH_ARM, uc_mode)
            self.mem = MemoryProxy(self._uc)
        self._reg_map = _build_arm_reg_map()

    def _init_riscv(self, mode: str, init_uc: bool, bits: int) -> None:
        from unicorn import Uc, UC_ARCH_RISCV, UC_MODE_RISCV32, UC_MODE_RISCV64
        from ..archs.arm.memory_proxy import MemoryProxy
        if init_uc:
            uc_mode = UC_MODE_RISCV32 if bits == 32 else UC_MODE_RISCV64
            self._uc = Uc(UC_ARCH_RISCV, uc_mode)
            self.mem = MemoryProxy(self._uc)
        self._reg_map = _build_riscv_reg_map()

    def _init_x86(self, mode: str, init_uc: bool, bits: int) -> None:
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_MODE_64
        from ..archs.arm.memory_proxy import MemoryProxy
        if init_uc:
            uc_mode = UC_MODE_64 if bits == 64 else UC_MODE_32
            self._uc = Uc(UC_ARCH_X86, uc_mode)
            self.mem = MemoryProxy(self._uc)
        self._reg_map = _build_x86_reg_map()

    # ---- uc property ----

    @property
    def uc(self) -> Any:
        if self._uc is None:
            raise RuntimeError("Unicorn backend was not initialized with a valid uc object")
        return self._uc

    # ---- memory ----

    def mem_map(self, addr: int, size: int, perms: int):
        return self.uc.mem_map(addr, size, perms)

    def mem_unmap(self, addr: int, size: int):
        return self.uc.mem_unmap(addr, size)

    def mem_read(self, addr: int, size: int) -> bytes:
        return bytes(self.uc.mem_read(addr, size))

    def mem_write(self, addr: int, data: bytes):
        return self.uc.mem_write(addr, data)

    def mem_regions(self):
        return list(self.uc.mem_regions())

    # ---- execution ----

    def emu_start(self, begin: int, end: int = 0):
        return self.uc.emu_start(begin, end)

    def emu_stop(self):
        return self.uc.emu_stop()

    # ---- hooks ----

    def hook_code(self, begin: int, end: int, hook):
        from unicorn import UC_HOOK_CODE
        callback = hook.hook_unicorn if hasattr(hook, "hook_unicorn") else hook
        return self.uc.hook_add(UC_HOOK_CODE, callback, None, begin, end)

    def hook_mem_read(self, begin: int, end: int, hook):
        from unicorn import UC_HOOK_MEM_READ
        callback = hook.hook_unicorn if hasattr(hook, "hook_unicorn") else hook
        return self.uc.hook_add(UC_HOOK_MEM_READ, callback, None, begin, end)

    def hook_mem_write(self, begin: int, end: int, hook):
        from unicorn import UC_HOOK_MEM_WRITE
        callback = hook.hook_unicorn if hasattr(hook, "hook_unicorn") else hook
        return self.uc.hook_add(UC_HOOK_MEM_WRITE, callback, None, begin, end)

    # ---- registers ----

    def get_register(self, name: str) -> int:
        key = name.upper()
        const = self._reg_map.get(key)
        if const is None:
            raise KeyError(f"Unsupported register '{name}'")
        return self.uc.reg_read(const)

    def set_register(self, name: str, value: int) -> None:
        key = name.upper()
        const = self._reg_map.get(key)
        if const is None:
            raise KeyError(f"Unsupported register '{name}'")
        self.uc.reg_write(const, value)


def create_unicorn_backend(arch: str, mode: str, **backend_kwargs):
    return UnicornBackend(arch, mode, **backend_kwargs)
