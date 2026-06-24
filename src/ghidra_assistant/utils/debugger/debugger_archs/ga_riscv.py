from __future__ import annotations

import struct

from .base_arch import BaseArch_debugger
from ...archs.riscv.riscv_concrete_state import RISCV_Concrete_State, RISCV32_Concrete_State, RISCV64_Concrete_State
from ...utils import error, warn


class GA_riscv_debugger(BaseArch_debugger):
    """RISC-V debugger backend for the Gupje transport protocol.

    Supports both rv32 and rv64 host packing formats.
    """

    def __init__(self, vector_table_addr: int, debugger_addr: int, storage_addr: int, bits: int = 64) -> None:
        super().__init__(vector_table_addr, debugger_addr, storage_addr)
        if bits not in (32, 64):
            raise ValueError(f"bits must be 32 or 64, got {bits}")

        self.bits = bits
        self._word_size = 8 if bits == 64 else 4
        self._ptr_fmt = "<Q" if bits == 64 else "<I"

        # Keep cs/ks/sc attributes present for compatibility with callers that
        # expect them, even when no RISCV shellcode helper is available.
        try:
            from capstone import Cs, CS_ARCH_RISCV, CS_MODE_RISCV32, CS_MODE_RISCV64

            mode = CS_MODE_RISCV32 if bits == 32 else CS_MODE_RISCV64
            self.cs = Cs(CS_ARCH_RISCV, mode)
            self.cs.detail = True
        except Exception:
            self.cs = None

        try:
            from keystone import Ks
            from keystone import KS_ARCH_RISCV, KS_MODE_RISCV32, KS_MODE_RISCV64

            mode = KS_MODE_RISCV32 if bits == 32 else KS_MODE_RISCV64
            self.ks = Ks(KS_ARCH_RISCV, mode)
        except Exception:
            self.ks = None

        self.sc = None

        if bits == 32:
            self.state = RISCV32_Concrete_State(storage_addr, self)
        elif bits == 64:
            self.state = RISCV64_Concrete_State(storage_addr, self)
        else:
            self.state = RISCV_Concrete_State(storage_addr, self, bits=bits)

    def _pack_addr(self, address: int) -> bytes:
        return struct.pack(self._ptr_fmt, int(address))

    def _pack_peek_poke_params(self, address: int, size: int) -> bytes:
        if self.bits == 64:
            return struct.pack("<QI", int(address), int(size))
        return struct.pack("<III", int(address), int(size), 0)

    def _unpack_addr(self, data: bytes) -> int:
        return struct.unpack(self._ptr_fmt, data[:self._word_size])[0]

    def create_debugger_vbar(self, *args, **kwargs):
        # ARM/ARM64-specific concept; RISC-V should use trap-vector setup.
        return NotImplemented

    def memwrite_io(self, address, data):
        assert len(data) < (0x20 - 12), "Data length is too long for IO write"
        self.write(b"HWIO")

        if self.bits == 64:
            packet = struct.pack("<QI", int(address), len(data)) + data
        else:
            packet = struct.pack("<III", int(address), 0, len(data)) + data

        packet += b"\x00" * (0x20 - len(packet))
        self.write(packet)
        self.read(self.transmission_size)

    def memdump_region(self, offset, size):
        mem_param = self._pack_peek_poke_params(offset, size)
        return self._memdump_region_impl(mem_param, size)

    def memwrite_region(self, address, data):
        size = len(data)
        mem_param = self._pack_peek_poke_params(address, size)
        self._memwrite_region_impl(mem_param, data)

    def get_debugger_location(self):
        self.write(b"SELF")
        d = self.read(4 if self.bits == 32 else 8)
        return self._unpack_addr(d)

    def read_vbar(self):
        return NotImplemented

    def write_vbar(self, address):
        return NotImplemented

    def disable_mmu(self):
        return NotImplemented

    def read_mmu(self):
        return NotImplemented

    def enable_mmu(self):
        return NotImplemented

    def jump_to(self, address):
        self.write(b"JUMP")
        self.write(self._pack_addr(address))

    def add_hook(self, hook_addr, use_smc=True):
        raise NotImplementedError("RISC-V add_hook is not implemented yet")

    def auto_debugger_setup(self):
        self.debugger_addr = self.get_debugger_location()
        # Keep the same shape as the ARM backends.
        self.state = self.state.__class__(self.storage_addr, self)
        self.special_regs = None

    def sync_state(self):
        self.write(b"SYNC")
        if self.read(0x100) != b"GiAs":
            warn("Debugger returned invalid response on syncing state")

    def sync_special_regs(self):
        self.write(b"SYNS")
        if self.read(0x100) != b"GiAs":
            warn("Debugger returned invalid response on syncing special state")

    def restore_stack_and_jump(self, address, stack: bytes = b""):
        self.state.DEBUGGER_JUMP = int(address)
        self.write(b"REST")

    def fetch_special_regs(self):
        self.write(b"SPEC")
        self.read(4)


class GA_riscv32_debugger(GA_riscv_debugger):
    def __init__(self, vector_table_addr: int, debugger_addr: int, storage_addr: int) -> None:
        super().__init__(vector_table_addr, debugger_addr, storage_addr, bits=32)


class GA_riscv64_debugger(GA_riscv_debugger):
    def __init__(self, vector_table_addr: int, debugger_addr: int, storage_addr: int) -> None:
        super().__init__(vector_table_addr, debugger_addr, storage_addr, bits=64)
