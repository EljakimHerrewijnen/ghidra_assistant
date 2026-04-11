from __future__ import annotations

from ...utils import info


_RISCV_ALIASES: dict[str, str] = {
    "ZERO": "X0",
    "RA": "X1",
    "SP": "X2",
    "GP": "X3",
    "TP": "X4",
    "T0": "X5",
    "T1": "X6",
    "T2": "X7",
    "S0": "X8",
    "FP": "X8",
    "S1": "X9",
    "A0": "X10",
    "A1": "X11",
    "A2": "X12",
    "A3": "X13",
    "A4": "X14",
    "A5": "X15",
    "A6": "X16",
    "A7": "X17",
    "S2": "X18",
    "S3": "X19",
    "S4": "X20",
    "S5": "X21",
    "S6": "X22",
    "S7": "X23",
    "S8": "X24",
    "S9": "X25",
    "S10": "X26",
    "S11": "X27",
    "T3": "X28",
    "T4": "X29",
    "T5": "X30",
    "T6": "X31",
    "PC": "PC",
}

_RISCV_ALL_REGS: frozenset[str] = frozenset({f"X{i}" for i in range(32)} | set(_RISCV_ALIASES.keys()))


class RiscvProcessorState:
    """Register-centric processor-state facade for RISC-V emulators.

    This class provides ARM64-style convenience access for register state,
    including ABI aliases (``a0``, ``sp``, ``ra``, ...), context dumping,
    and context restore.
    """

    def __init__(self, emulator, bits: int | None = None) -> None:
        object.__setattr__(self, "emulator", emulator)
        if bits is None:
            bits = int(getattr(emulator, "_bits", 64))
        if bits not in (32, 64):
            raise ValueError(f"bits must be 32 or 64, got {bits}")
        object.__setattr__(self, "bits", bits)
        object.__setattr__(self, "_mask", (1 << bits) - 1)

    # ------- register resolution -------

    def _canonical_register_name(self, name: str) -> str:
        upper = name.upper()
        if upper.startswith("X") and upper[1:].isdigit():
            idx = int(upper[1:])
            if 0 <= idx <= 31:
                return upper
        canonical = _RISCV_ALIASES.get(upper)
        if canonical is None:
            raise KeyError(f"Unsupported RISC-V register '{name}'")
        return canonical

    def read_reg(self, name: str) -> int:
        canonical = self._canonical_register_name(name)
        return int(self.emulator.get_register(canonical)) & self._mask

    def write_reg(self, name: str, value: int) -> None:
        canonical = self._canonical_register_name(name)
        if canonical == "X0":
            # x0 is hard-wired to 0 by architecture definition.
            return
        self.emulator.set_register(canonical, int(value) & self._mask)

    # ------- dynamic attribute register access -------

    def __getattr__(self, name: str):
        upper = name.upper()
        if upper in _RISCV_ALL_REGS:
            return self.read_reg(upper)
        raise AttributeError(name)

    def __setattr__(self, name: str, value) -> None:
        upper = name.upper()
        if upper in _RISCV_ALL_REGS:
            self.write_reg(upper, value)
            return
        object.__setattr__(self, name, value)

    # ------- context helpers -------

    def restore_ctx(self, ctx: dict[str, int]) -> None:
        for reg, value in ctx.items():
            try:
                self.write_reg(reg, value)
            except KeyError:
                continue

    def get_ctx(self, as_dict: bool = False):
        ctx = {f"X{i}": self.read_reg(f"X{i}") for i in range(32)}
        ctx["PC"] = self.read_reg("PC")
        if as_dict:
            return ctx

        lines = []
        for i in range(0, 32, 4):
            lines.append(
                " ".join([f"X{i + j:02}: 0x{ctx[f'X{i + j}']:0{self.bits // 4}x}" for j in range(4)])
            )
        lines.append(f" PC: 0x{ctx['PC']:0{self.bits // 4}x}")
        return "\n".join(lines)

    def print_ctx(self) -> None:
        info(self.get_ctx())


class Riscv32ProcessorState(RiscvProcessorState):
    def __init__(self, emulator) -> None:
        super().__init__(emulator, bits=32)


class Riscv64ProcessorState(RiscvProcessorState):
    def __init__(self, emulator) -> None:
        super().__init__(emulator, bits=64)
