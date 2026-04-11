from __future__ import annotations

import struct

from ghidra_assistant.utils.debugger.debugger_archs.ga_riscv import GA_riscv32_debugger, GA_riscv64_debugger
from ghidra_assistant.utils.archs.riscv.riscv_concrete_state import RISCV64_Concrete_State


class _Transport:
    def __init__(self):
        self.read_queue: list[bytes] = []
        self.writes: list[bytes] = []

    def queue(self, *chunks: bytes) -> None:
        self.read_queue.extend(chunks)

    def write(self, data: bytes) -> None:
        self.writes.append(data)

    def read(self, n: int) -> bytes:
        if not self.read_queue:
            raise RuntimeError("no queued read data")
        return self.read_queue.pop(0)


class _MemoryDebugger:
    def __init__(self, base: int):
        self.base = base
        self.mem: dict[int, bytes] = {}

    def memwrite_region(self, addr: int, data: bytes):
        self.mem[addr] = bytes(data)

    def memdump_region(self, addr: int, size: int) -> bytes:
        return self.mem.get(addr, b"\x00" * size)

    def sync_state(self):
        return None

    def sync_special_regs(self):
        return None


def test_ga_riscv32_memdump_uses_32bit_packet_layout() -> None:
    tr = _Transport()
    dbg = GA_riscv32_debugger(0x1000, 0x2000, 0x3000)
    dbg.read = tr.read
    dbg.write = tr.write
    dbg.transmission_size = 4

    tr.queue(b"\x11\x22\x33\x44")

    out = dbg.memdump_region(0x1234, 4)

    assert out == b"\x11\x22\x33\x44"
    assert tr.writes[0] == b"PEEK"
    assert tr.writes[1] == struct.pack("<III", 0x1234, 4, 0)


def test_ga_riscv64_get_debugger_location_uses_64bit_pointer() -> None:
    tr = _Transport()
    dbg = GA_riscv64_debugger(0x1000, 0x2000, 0x3000)
    dbg.read = tr.read
    dbg.write = tr.write

    ptr = 0x1122334455667788
    tr.queue(struct.pack("<Q", ptr))

    got = dbg.get_debugger_location()

    assert got == ptr
    assert tr.writes[0] == b"SELF"


def test_riscv64_concrete_state_register_aliases_and_debug_slot() -> None:
    base = 0x100000
    md = _MemoryDebugger(base)
    state = RISCV64_Concrete_State(base, md)

    state.A0 = 0x1234
    assert state.X10 == 0x1234

    state.X0 = 0xFFFF
    assert state.X0 == 0

    state.DEBUGGER_JUMP = 0xDEADBEEF
    assert state.DEBUGGER_JUMP == 0xDEADBEEF

    slot_addr = base + (511 * 8)
    assert md.mem[slot_addr] == struct.pack("<Q", 0xDEADBEEF)
