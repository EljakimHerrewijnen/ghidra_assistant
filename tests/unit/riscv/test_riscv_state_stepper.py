from __future__ import annotations

import pytest

pytest.importorskip("unicorn")
pytest.importorskip("capstone")

from ghidra_assistant.utils.archs.riscv.riscv_emulator import RiscvEmulator
from ghidra_assistant.utils.archs.riscv.riscv_processor_state import RiscvProcessorState
from ghidra_assistant.utils.archs.riscv.riscv_stepper import RiscvStepper


# addi x1, x0, 5
ADDI_X1_X0_5 = b"\x93\x00\x50\x00"
# addi x2, x1, 3
ADDI_X2_X1_3 = b"\x13\x81\x30\x00"


def test_riscv64_processor_state_aliases_and_x0_immutability() -> None:
    emu = RiscvEmulator(bits=64)
    state = RiscvProcessorState(emu, bits=64)

    state.a0 = 0x1234
    assert state.A0 == 0x1234
    assert state.X10 == 0x1234

    state.zero = 0xFFFF
    assert state.ZERO == 0
    assert state.X0 == 0

    state.pc = 0x4000
    assert state.PC == 0x4000


def test_riscv32_stepper_executes_single_instructions() -> None:
    emu = RiscvEmulator(bits=32)
    base = 0x1000

    emu.mem_map(base, 0x1000, 7)
    emu.mem_write(base, ADDI_X1_X0_5 + ADDI_X2_X1_3)

    state = RiscvProcessorState(emu, bits=32)
    state.PC = base

    stepper = RiscvStepper(emu, state)

    pc1 = stepper.step()
    assert pc1 == base + 4
    assert state.X1 == 5

    pc2 = stepper.step()
    assert pc2 == base + 8
    assert state.X2 == 8


def test_riscv32_get_next_addr_tracks_sequential_flow() -> None:
    emu = RiscvEmulator(bits=32)
    base = 0x2000

    emu.mem_map(base, 0x1000, 7)
    emu.mem_write(base, ADDI_X1_X0_5)

    state = RiscvProcessorState(emu, bits=32)
    state.PC = base

    stepper = RiscvStepper(emu, state)
    assert stepper.get_next_addr() == base + 4
