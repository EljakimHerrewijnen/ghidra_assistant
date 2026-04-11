import struct
from types import SimpleNamespace

from ghidra_assistant.utils.debugger.gdb_rsp.aarch64 import AArch64ConcreteGDBTarget, REGISTERS
from ghidra_assistant.utils.debugger.gdb_rsp.protocol import StopReply


class _FakeState:
    def __init__(self) -> None:
        for index in range(31):
            setattr(self, f"X{index}", 0x1000 + index)
        self.SP = 0x2000
        self.NZCV = 0x40000000
        self.DAIF = 0
        self.ELR_EL3 = 0x4000
        self.ELR_EL2 = 0x5000
        self.ELR_EL1 = 0x6000
        self.DEBUGGER_JUMP = 0x7000
        self.R_CURRENT_EL = SimpleNamespace(get_exception_level=lambda: 3)


class _FakeConcreteDevice:
    def __init__(self) -> None:
        self.memory: dict[int, int] = {}
        self.ga_stack_location = 0x9000
        self.arch_dbg = SimpleNamespace(
            state=_FakeState(),
            debugger_addr=0xD00D0000,
            storage_addr=0x3000,
            ks=None,
            sc=SimpleNamespace(branch_absolute=lambda address: b"\xCC" * 16),
        )
        self.sync_calls = 0
        self.fetch_calls = 0
        self.reads: list[tuple[int, int]] = []
        self.writes: list[tuple[int, bytes]] = []
        self.restore_calls: list[int] = []
        self.read_requests: list[int] = []
        self.read_queue: list[bytes] = [b"GiAs"]
        self.breakpoint_markers: list[int | None] = []

    def fetch_special_regs(self) -> None:
        self.fetch_calls += 1

    def sync_state(self) -> None:
        self.sync_calls += 1

    def memdump_region(self, address: int, length: int) -> bytes:
        self.reads.append((address, length))
        return bytes(self.memory.get(address + offset, offset & 0xFF) for offset in range(length))

    def memwrite_region(self, address: int, data: bytes) -> None:
        self.writes.append((address, bytes(data)))
        for offset, value in enumerate(data):
            self.memory[address + offset] = value

    def restore_stack_and_jump(self, address: int) -> None:
        self.restore_calls.append(address)
        if self.breakpoint_markers:
            marker = self.breakpoint_markers.pop(0)
            if marker is not None:
                data = struct.pack("<Q", marker)
                for offset, value in enumerate(data):
                    self.memory[self.arch_dbg.storage_addr + (509 * 8) + offset] = value

    def read(self, length: int) -> bytes:
        self.read_requests.append(length)
        if not self.read_queue:
            raise RuntimeError("no queued read data")
        return self.read_queue.pop(0)


class _FakeStepper:
    instances: list["_FakeStepper"] = []

    def __init__(self, concrete_device, pc: int) -> None:
        self.cd = concrete_device
        self.pc = pc
        self.step_calls = 0
        self.__class__.instances.append(self)

    def step(self) -> None:
        self.step_calls += 1
        self.pc += 4


def test_read_all_registers_marks_x15_unavailable_and_uses_elr_for_pc() -> None:
    target = AArch64ConcreteGDBTarget(_FakeConcreteDevice())

    payload = target.read_all_registers()

    widths = [descriptor.width * 2 for descriptor in REGISTERS]
    chunks = []
    offset = 0
    for width in widths:
        chunks.append(payload[offset : offset + width])
        offset += width

    assert chunks[0] == (0x1000).to_bytes(8, "little").hex()
    assert chunks[15] == "x" * 16
    assert chunks[31] == (0x2000).to_bytes(8, "little").hex()
    assert chunks[32] == (0x4000).to_bytes(8, "little").hex()
    assert chunks[33] == (0x40000000).to_bytes(4, "little").hex()


def test_read_all_registers_falls_back_to_debugger_jump_when_elr_is_not_available() -> None:
    device = _FakeConcreteDevice()
    device.arch_dbg.state.ELR_EL3 = 0
    target = AArch64ConcreteGDBTarget(device)

    assert target.read_register(32) == (0x7000).to_bytes(8, "little").hex()


def test_read_all_registers_falls_back_to_configured_start_pc_when_state_has_no_pc() -> None:
    device = _FakeConcreteDevice()
    device.arch_dbg.state.ELR_EL3 = 0
    device.arch_dbg.state.DEBUGGER_JUMP = 0
    target = AArch64ConcreteGDBTarget(device, start_pc=0x96000)

    assert target.read_register(32) == (0x96000).to_bytes(8, "little").hex()


def test_continue_execution_uses_configured_start_pc_when_no_current_pc_exists() -> None:
    device = _FakeConcreteDevice()
    device.arch_dbg.state.ELR_EL3 = 0
    device.arch_dbg.state.DEBUGGER_JUMP = 0
    target = AArch64ConcreteGDBTarget(device, start_pc=0x96000)

    reply = target.continue_execution()

    assert reply == StopReply(signal=5)
    assert device.restore_calls == [0x96000]


def test_write_all_registers_updates_supported_registers_and_syncs_once() -> None:
    device = _FakeConcreteDevice()
    target = AArch64ConcreteGDBTarget(device)

    data = []
    for descriptor in REGISTERS:
        if descriptor.name == "x15":
            data.append("x" * (descriptor.width * 2))
        elif descriptor.name == "pc":
            data.append((0x7777).to_bytes(descriptor.width, "little").hex())
        elif descriptor.name == "cpsr":
            data.append((0x80000000).to_bytes(descriptor.width, "little").hex())
        else:
            data.append((0xABCD).to_bytes(descriptor.width, "little").hex())

    target.write_all_registers("".join(data))

    assert device.arch_dbg.state.X0 == 0xABCD
    assert device.arch_dbg.state.X14 == 0xABCD
    assert device.arch_dbg.state.X15 == 0x1000 + 15
    assert device.arch_dbg.state.SP == 0xABCD
    assert device.arch_dbg.state.NZCV == 0x80000000
    assert target.read_register(32) == (0x7777).to_bytes(8, "little").hex()
    assert device.sync_calls == 1


def test_memory_access_delegates_to_concrete_device() -> None:
    device = _FakeConcreteDevice()
    target = AArch64ConcreteGDBTarget(device)

    assert target.read_memory(0x5000, 4) == b"\x00\x01\x02\x03"
    target.write_memory(0x6000, b"\xAA\xBB")

    assert device.reads[-1] == (0x5000, 4)
    assert device.writes[-1] == (0x6000, b"\xAA\xBB")


def test_continue_execution_uses_restore_stack_and_jump_and_waits_for_debugger_banner() -> None:
    device = _FakeConcreteDevice()
    target = AArch64ConcreteGDBTarget(device)

    reply = target.continue_execution(0x7000)

    assert reply == StopReply(signal=5)
    assert device.restore_calls == [0x7000]
    assert device.read_requests == [4]


def test_step_instruction_uses_stepper_factory_and_updates_pc() -> None:
    _FakeStepper.instances.clear()
    device = _FakeConcreteDevice()
    target = AArch64ConcreteGDBTarget(device, stepper_factory=_FakeStepper)

    reply = target.step_instruction(0x9000)

    assert reply == StopReply(signal=5)
    assert _FakeStepper.instances[0].step_calls == 1
    assert target.read_register(32) == (0x9004).to_bytes(8, "little").hex()


def test_insert_and_remove_software_breakpoint_patches_memory() -> None:
    device = _FakeConcreteDevice()
    for offset in range(16):
        device.memory[0x5000 + offset] = offset
    target = AArch64ConcreteGDBTarget(device)

    target.insert_software_breakpoint(0x5000, 4)

    assert any(write == (0x5000, b"\xCC" * 16) for write in device.writes)

    target.remove_software_breakpoint(0x5000, 4)

    assert device.writes[-1] == (0x5000, bytes(range(16)))


def test_breakpoint_hit_reports_swbreak_and_restores_original_bytes() -> None:
    device = _FakeConcreteDevice()
    for offset in range(16):
        device.memory[0x6000 + offset] = offset + 1
    target = AArch64ConcreteGDBTarget(device)
    target.insert_software_breakpoint(0x6000, 4)
    device.breakpoint_markers = [1]

    reply = target.continue_execution(0x4000)

    assert reply == StopReply(signal=5, reason="swbreak")
    assert target.stop_reply().to_payload() == "T05swbreak:;"
    assert (0x6000, bytes(range(1, 17))) in device.writes
    assert target.read_register(32) == (0x6000).to_bytes(8, "little").hex()


def test_step_instruction_steps_over_pending_breakpoint_and_rearms_it() -> None:
    _FakeStepper.instances.clear()
    device = _FakeConcreteDevice()
    for offset in range(16):
        device.memory[0x7000 + offset] = 0x41 + offset
    target = AArch64ConcreteGDBTarget(device, stepper_factory=_FakeStepper)
    target.insert_software_breakpoint(0x7000, 4)
    device.breakpoint_markers = [1]

    target.continue_execution(0x4000)
    reply = target.step_instruction(0x7000)

    assert reply == StopReply(signal=5)
    assert _FakeStepper.instances[-1].step_calls == 1
    assert target.read_register(32) == (0x7004).to_bytes(8, "little").hex()
    assert (0x7000, b"\xCC" * 16) in device.writes


def test_multiple_breakpoints_can_be_inserted_and_second_hit_is_identified() -> None:
    device = _FakeConcreteDevice()
    target = AArch64ConcreteGDBTarget(device)
    for offset in range(16):
        device.memory[0x8000 + offset] = 0x21 + offset
        device.memory[0x9000 + offset] = 0x31 + offset

    target.insert_software_breakpoint(0x8000, 4)
    target.insert_software_breakpoint(0x9000, 4)
    device.breakpoint_markers = [2]

    reply = target.continue_execution(0x4000)

    assert reply == StopReply(signal=5, reason="swbreak")
    assert target.read_register(32) == (0x9000).to_bytes(8, "little").hex()