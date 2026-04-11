from types import SimpleNamespace

import pytest

pytest.importorskip("capstone")
pytest.importorskip("keystone")

from keystone import KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN, Ks

from ghidra_assistant.utils.archs.arm64.arm64_stepper import ARM64Stepper
from ghidra_assistant.utils.archs.arm64.arm64_exception_stepper import ARM64ExceptionStepper
from ghidra_assistant.utils.archs.arm64.asm_arm64 import ShellcodeCrafterARM64


ASSEMBLER = Ks(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN)


class _CurrentEL:
    def get_exception_level(self) -> int:
        return 3


class _FakeNZCV:
    def condition_met(self, _condition: str) -> bool:
        return False


class _FakeState:
    def __init__(self) -> None:
        self.R_CURRENT_EL = _CurrentEL()
        self.R_NZCV = _FakeNZCV()
        self.VBAR_EL1 = 0x111000
        self.VBAR_EL2 = 0x222000
        self.VBAR_EL3 = 0x333000
        self.X0 = 1


def _assemble(source: str, address: int) -> bytes:
    return ASSEMBLER.asm(source, addr=address, as_bytes=True)[0]


def _write_memory(device: "_FakeConcreteDevice", address: int, data: bytes) -> None:
    for offset, value in enumerate(data):
        device.memory[address + offset] = value


def _make_arch_debugger(*, with_sync_special_regs: bool = True, with_create_debugger_vbar: bool = True):
    shellcode = ShellcodeCrafterARM64(None, None)
    state = _FakeState()
    arch_dbg = SimpleNamespace(
        sc=shellcode,
        ks=shellcode.ks,
        cs=shellcode.cs,
        state=state,
        debugger_addr=0x81000,
        vector_table_addr=0x82000,
        storage_addr=0x85000,
        vbar_el3_original=0,
        synced_vbars=[],
    )

    if with_sync_special_regs:
        def sync_special_regs() -> None:
            arch_dbg.synced_vbars.append(state.VBAR_EL3)

        arch_dbg.sync_special_regs = sync_special_regs

    if with_create_debugger_vbar:
        def create_debugger_vbar() -> bytes:
            return b"\xAA" * 0x800

        arch_dbg.create_debugger_vbar = create_debugger_vbar

    return arch_dbg


class _FakeConcreteDevice:
    def __init__(self, arch_dbg) -> None:
        self.arch_dbg = arch_dbg
        self.memory: dict[int, int] = {}
        self.fetch_calls = 0
        self.read_queue = [b"GiAs", b"GiAs", b"GiAs", b"GiAs"]
        self.read_requests: list[int] = []
        self.restore_calls: list[int] = []
        self.writes: list[tuple[int, bytes]] = []
        self.commands: list[bytes] = []

    def fetch_special_regs(self) -> None:
        self.fetch_calls += 1

    def memdump_region(self, address: int, length: int) -> bytes:
        return bytes(self.memory.get(address + offset, 0) for offset in range(length))

    def memwrite_region(self, address: int, data: bytes) -> None:
        self.writes.append((address, bytes(data)))
        _write_memory(self, address, data)

    def restore_stack_and_jump(self, address: int) -> None:
        self.restore_calls.append(address)

    def read(self, length: int) -> bytes:
        self.read_requests.append(length)
        if not self.read_queue:
            raise RuntimeError("no queued read data")
        return self.read_queue.pop(0)

    def write(self, data: bytes) -> None:
        self.commands.append(data)


def test_exception_step_swaps_vbar_restores_it_and_advances_pc() -> None:
    arch_dbg = _make_arch_debugger()
    device = _FakeConcreteDevice(arch_dbg)
    original_vbar = 0x444000
    _write_memory(device, 0x1000, _assemble("smc #0x7777", 0x1000))

    stepper = ARM64ExceptionStepper(device, 0x1000, original_vbar=original_vbar, use_backend_vbar_sync=True)
    stepper.step()

    assert device.fetch_calls == 1
    assert device.restore_calls == [0x1000]
    assert device.read_requests == [4]
    assert stepper.pc == 0x1004
    assert arch_dbg.state.VBAR_EL3 == original_vbar
    assert arch_dbg.synced_vbars == [arch_dbg.vector_table_addr, original_vbar]
    assert (arch_dbg.vector_table_addr, b"\xAA" * 0x800) in device.writes


def test_exception_step_falls_back_to_direct_vbar_swap_when_backend_sync_fails() -> None:
    arch_dbg = _make_arch_debugger()

    def sync_special_regs() -> None:
        raise TimeoutError("SYNS timed out")

    arch_dbg.sync_special_regs = sync_special_regs
    device = _FakeConcreteDevice(arch_dbg)
    _write_memory(device, 0x1000, _assemble("smc #0x7777", 0x1000))

    stepper = ARM64ExceptionStepper(device, 0x1000)
    stepper.step()

    scratch_addr = arch_dbg.storage_addr + 0x400
    assert device.fetch_calls == 1
    assert device.restore_calls == [scratch_addr, scratch_addr]
    assert device.read_requests == [4, 4]
    assert stepper.pc == 0x1004
    assert arch_dbg.synced_vbars == []
    assert arch_dbg.state.VBAR_EL3 == 0x333000
    assert (arch_dbg.vector_table_addr, b"\xAA" * 0x800) in device.writes


def test_exception_step_requires_create_debugger_vbar_support() -> None:
    arch_dbg = _make_arch_debugger(
        with_sync_special_regs=True,
        with_create_debugger_vbar=False,
    )
    device = _FakeConcreteDevice(arch_dbg)
    _write_memory(device, 0x1000, _assemble("smc #0x7777", 0x1000))

    stepper = ARM64ExceptionStepper(device, 0x1000)

    with pytest.raises(RuntimeError, match="create_debugger_vbar"):
        stepper.step()

    assert device.restore_calls == []


def test_conditional_step_patches_both_branch_target_and_fallthrough() -> None:
    arch_dbg = _make_arch_debugger()
    device = _FakeConcreteDevice(arch_dbg)
    _write_memory(device, 0x1000, _assemble("cbz x0, #0x1010", 0x1000))
    _write_memory(device, 0x1004, b"ABCD")
    _write_memory(device, 0x1010, b"WXYZ")

    stepper = ARM64ExceptionStepper(device, 0x1000, use_breakpoint_stepping=True, use_backend_vbar_sync=True)
    stepper.step()

    assert device.fetch_calls == 1
    assert device.restore_calls == [0x1000]
    assert stepper.pc == 0x1004
    assert arch_dbg.synced_vbars == [arch_dbg.vector_table_addr, 0x333000]
    assert (0x1004, arch_dbg.sc.brk_ins) in device.writes
    assert (0x1010, arch_dbg.sc.brk_ins) in device.writes
    assert device.memdump_region(0x1004, 4) == b"ABCD"
    assert device.memdump_region(0x1010, 4) == b"WXYZ"


def test_non_exception_step_falls_back_to_base_stepper_when_backend_sync_fails(monkeypatch) -> None:
    arch_dbg = _make_arch_debugger()

    def sync_special_regs() -> None:
        raise TimeoutError("SYNS timed out")

    arch_dbg.sync_special_regs = sync_special_regs
    device = _FakeConcreteDevice(arch_dbg)
    _write_memory(device, 0x1000, _assemble("nop", 0x1000))
    calls = []

    def fake_step(self) -> None:
        calls.append(self.pc)
        self.pc += 4

    monkeypatch.setattr(ARM64Stepper, "step", fake_step)

    stepper = ARM64ExceptionStepper(device, 0x1000, use_breakpoint_stepping=True)
    stepper.step()

    assert calls == [0x1000]
    assert stepper.pc == 0x1004