from __future__ import annotations

from ...utils import debug
from .riscv_processor_state import RiscvProcessorState


_BRANCH_MNEMONICS = {
    "beq", "bne", "blt", "bge", "bltu", "bgeu",
}

_UNCOND_JUMP_MNEMONICS = {
    "j", "jal", "ret", "jalr",
}


class RiscvStepper:
    """Instruction-step helper for RISC-V emulators.

    The stepper executes exactly one instruction via Unicorn's ``count=1``
    mechanism, so it remains correct for both 16-bit compressed and 32-bit
    instruction encodings.
    """

    def __init__(self, emulator, state: RiscvProcessorState | None = None, debug_log: bool = False) -> None:
        self.emulator = emulator
        self.state = state if state is not None else RiscvProcessorState(emulator)
        self.debug_log = debug_log

    @property
    def pc(self) -> int:
        return self.state.read_reg("PC")

    @pc.setter
    def pc(self, value: int) -> None:
        self.state.write_reg("PC", value)

    def _decode_current(self):
        insns = self.emulator.disasm(self.pc, dlen=8)
        if not insns:
            return None
        return insns[0]

    def _parse_imm(self, token: str) -> int | None:
        try:
            return int(token.strip(), 0)
        except ValueError:
            return None

    def _to_signed(self, value: int) -> int:
        bits = self.state.bits
        sign = 1 << (bits - 1)
        mask = (1 << bits) - 1
        value &= mask
        return (value ^ sign) - sign

    def get_next_addr(self) -> int:
        insn = self._decode_current()
        if insn is None:
            return self.pc

        mnemonic = insn.mnemonic.lower()
        next_seq = self.pc + int(insn.size)

        if mnemonic in _UNCOND_JUMP_MNEMONICS | _BRANCH_MNEMONICS:
            parts = [p.strip() for p in insn.op_str.split(",") if p.strip()]

            if mnemonic == "ret":
                return self.state.read_reg("RA")

            if mnemonic in {"j", "jal"} and parts:
                target = self._parse_imm(parts[-1])
                return target if target is not None else next_seq

            if mnemonic == "jalr":
                # jalr rd, rs1, imm
                if len(parts) >= 2:
                    base_reg = parts[1]
                    imm = self._parse_imm(parts[2]) if len(parts) >= 3 else 0
                    if imm is None:
                        imm = 0
                    base = self.state.read_reg(base_reg)
                    return (base + imm) & ~1
                return next_seq

            # Conditional branches: beq rs1, rs2, target
            if len(parts) >= 3:
                rs1 = self.state.read_reg(parts[0])
                rs2 = self.state.read_reg(parts[1])
                target = self._parse_imm(parts[2])
                if target is None:
                    return next_seq

                if mnemonic == "beq" and rs1 == rs2:
                    return target
                if mnemonic == "bne" and rs1 != rs2:
                    return target
                if mnemonic == "blt" and self._to_signed(rs1) < self._to_signed(rs2):
                    return target
                if mnemonic == "bge" and self._to_signed(rs1) >= self._to_signed(rs2):
                    return target
                if mnemonic == "bltu" and rs1 < rs2:
                    return target
                if mnemonic == "bgeu" and rs1 >= rs2:
                    return target

        return next_seq

    def step(self) -> int:
        start_pc = self.pc
        if self.debug_log:
            debug(f"riscv step: pc={start_pc:#x}")

        # Execute one instruction regardless of encoding width.
        self.emulator.uc.emu_start(start_pc, 0, 0, 1)
        end_pc = self.pc

        if self.debug_log:
            debug(f"riscv step done: next_pc={end_pc:#x}")

        return end_pc

    def run(self, start: int | None = None, end: int | None = None, max_steps: int = 0x10000) -> int:
        if start is not None:
            self.pc = start

        steps = 0
        while True:
            if end is not None and self.pc == end:
                break
            if max_steps >= 0 and steps >= max_steps:
                break
            self.step()
            steps += 1
        return steps
