from __future__ import annotations

import struct
import typing

from ...utils import info

if typing.TYPE_CHECKING:
    from ...debugger.debugger_archs.ga_riscv import GA_riscv_debugger


# Core register slots in storage.
X0 = 0
X1 = 1
X2 = 2
X3 = 3
X4 = 4
X5 = 5
X6 = 6
X7 = 7
X8 = 8
X9 = 9
X10 = 10
X11 = 11
X12 = 12
X13 = 13
X14 = 14
X15 = 15
X16 = 16
X17 = 17
X18 = 18
X19 = 19
X20 = 20
X21 = 21
X22 = 22
X23 = 23
X24 = 24
X25 = 25
X26 = 26
X27 = 27
X28 = 28
X29 = 29
X30 = 30
X31 = 31
PC = 32

# Debugger control slots (kept aligned with existing ARM/ARM64 layout).
DBG_MMU_INTERACT = 506
DBG_JUMP_TO = 507
DBG_CONT_EXEC = 508
TEMP_STORAGE = 509
EXCEPTION_ID = 510
JUMP_ADDR = 511


_ALIAS_TO_REG = {
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


class RISCV_Concrete_State:
    """Concrete-device storage mapper for RISC-V register/debugger state."""

    def __init__(self, base_config_address: int, debugger: "GA_riscv_debugger", bits: int = 64,
                 auto_sync: bool = False, auto_sync_special: bool = False) -> None:
        if bits not in (32, 64):
            raise ValueError(f"bits must be 32 or 64, got {bits}")

        object.__setattr__(self, "baddr", base_config_address)
        object.__setattr__(self, "debugger", debugger)
        object.__setattr__(self, "auto_sync", auto_sync)
        object.__setattr__(self, "auto_sync_special", auto_sync_special)
        object.__setattr__(self, "bits", bits)
        object.__setattr__(self, "_word_size", 8 if bits == 64 else 4)
        object.__setattr__(self, "_fmt", "<Q" if bits == 64 else "<I")
        object.__setattr__(self, "_mask", (1 << bits) - 1)

    def config_addr(self, config: int) -> int:
        return self.baddr + config * self._word_size

    def read_config(self, config: int) -> int:
        raw = self.debugger.memdump_region(self.config_addr(config), self._word_size)
        return struct.unpack(self._fmt, raw)[0]

    def write_config(self, config: int, value: int, do_not_sync: bool = False) -> None:
        masked = int(value) & self._mask
        self.debugger.memwrite_region(self.config_addr(config), struct.pack(self._fmt, masked))

        if do_not_sync:
            return
        if self.auto_sync:
            self.debugger.sync_state()
        if self.auto_sync_special:
            self.debugger.sync_special_regs()

    def _resolve_reg(self, name: str) -> str:
        upper = name.upper()
        if upper.startswith("X") and upper[1:].isdigit() and 0 <= int(upper[1:]) <= 31:
            return upper
        alias = _ALIAS_TO_REG.get(upper)
        if alias is None:
            raise KeyError(f"Unsupported RISC-V register '{name}'")
        return alias

    def _reg_slot(self, name: str) -> int:
        canonical = self._resolve_reg(name)
        if canonical == "PC":
            return PC
        return int(canonical[1:])

    def restore_ctx(self, ctx: dict[str, int]) -> None:
        for reg, value in ctx.items():
            try:
                self.__setattr__(reg, value)
            except (KeyError, AttributeError):
                continue

        if self.auto_sync:
            self.debugger.sync_state()

    def get_ctx(self, as_dict: bool = False):
        ctx = {f"X{i}": self.read_config(i) for i in range(32)}
        ctx["PC"] = self.read_config(PC)

        if as_dict:
            return ctx

        width = self.bits // 4
        lines = []
        for i in range(0, 32, 4):
            lines.append(
                " ".join([f"X{i + j:02}: 0x{ctx[f'X{i + j}']:0{width}x}" for j in range(4)])
            )
        lines.append(f" PC: 0x{ctx['PC']:0{width}x}")
        return "\n".join(lines)

    def print_ctx(self, print_fn=info) -> None:
        print_fn(self.get_ctx())

    def mem_read(self, address: int, length: int) -> bytes:
        return self.debugger.memdump_region(address, length)

    def mem_write(self, address: int, data: bytes) -> None:
        self.debugger.memwrite_region(address, data)

    def __getattr__(self, name: str):
        upper = name.upper()

        if upper in {"DBG_MMU_INTERACT", "DBG_JUMP_TO", "DBG_CONT_EXEC", "EXCEPTION_ID", "DEBUGGER_JUMP"}:
            mapping = {
                "DBG_MMU_INTERACT": DBG_MMU_INTERACT,
                "DBG_JUMP_TO": DBG_JUMP_TO,
                "DBG_CONT_EXEC": DBG_CONT_EXEC,
                "EXCEPTION_ID": EXCEPTION_ID,
                "DEBUGGER_JUMP": JUMP_ADDR,
            }
            return self.read_config(mapping[upper])

        try:
            return self.read_config(self._reg_slot(upper))
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value) -> None:
        upper = name.upper()

        if upper in {"DBG_MMU_INTERACT", "DBG_JUMP_TO", "DBG_CONT_EXEC", "EXCEPTION_ID", "DEBUGGER_JUMP"}:
            mapping = {
                "DBG_MMU_INTERACT": DBG_MMU_INTERACT,
                "DBG_JUMP_TO": DBG_JUMP_TO,
                "DBG_CONT_EXEC": DBG_CONT_EXEC,
                "EXCEPTION_ID": EXCEPTION_ID,
                "DEBUGGER_JUMP": JUMP_ADDR,
            }
            self.write_config(mapping[upper], int(value), do_not_sync=True)
            return

        try:
            slot = self._reg_slot(upper)
        except KeyError:
            object.__setattr__(self, name, value)
            return

        # X0 is architecturally read-only zero.
        if slot == 0:
            return

        self.write_config(slot, int(value), do_not_sync=False)


class RISCV32_Concrete_State(RISCV_Concrete_State):
    def __init__(self, base_config_address: int, debugger: "GA_riscv_debugger", auto_sync: bool = False,
                 auto_sync_special: bool = False) -> None:
        super().__init__(base_config_address, debugger, bits=32,
                         auto_sync=auto_sync, auto_sync_special=auto_sync_special)


class RISCV64_Concrete_State(RISCV_Concrete_State):
    def __init__(self, base_config_address: int, debugger: "GA_riscv_debugger", auto_sync: bool = False,
                 auto_sync_special: bool = False) -> None:
        super().__init__(base_config_address, debugger, bits=64,
                         auto_sync=auto_sync, auto_sync_special=auto_sync_special)
