from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from .protocol import StopReply, decode_uint_le, encode_uint_le, encode_unavailable

if TYPE_CHECKING:
    from ....concrete_device import ConcreteDevice


TARGET_XML = """<?xml version="1.0"?>
<!DOCTYPE target SYSTEM "gdb-target.dtd">
<target version="1.0">
  <architecture>aarch64</architecture>
  <feature name="org.gnu.gdb.aarch64.core">
    <reg name="x0" bitsize="64"/>
    <reg name="x1" bitsize="64"/>
    <reg name="x2" bitsize="64"/>
    <reg name="x3" bitsize="64"/>
    <reg name="x4" bitsize="64"/>
    <reg name="x5" bitsize="64"/>
    <reg name="x6" bitsize="64"/>
    <reg name="x7" bitsize="64"/>
    <reg name="x8" bitsize="64"/>
    <reg name="x9" bitsize="64"/>
    <reg name="x10" bitsize="64"/>
    <reg name="x11" bitsize="64"/>
    <reg name="x12" bitsize="64"/>
    <reg name="x13" bitsize="64"/>
    <reg name="x14" bitsize="64"/>
    <reg name="x15" bitsize="64"/>
    <reg name="x16" bitsize="64"/>
    <reg name="x17" bitsize="64"/>
    <reg name="x18" bitsize="64"/>
    <reg name="x19" bitsize="64"/>
    <reg name="x20" bitsize="64"/>
    <reg name="x21" bitsize="64"/>
    <reg name="x22" bitsize="64"/>
    <reg name="x23" bitsize="64"/>
    <reg name="x24" bitsize="64"/>
    <reg name="x25" bitsize="64"/>
    <reg name="x26" bitsize="64"/>
    <reg name="x27" bitsize="64"/>
    <reg name="x28" bitsize="64"/>
    <reg name="x29" bitsize="64"/>
    <reg name="x30" bitsize="64"/>
    <reg name="sp" bitsize="64" type="data_ptr"/>
    <reg name="pc" bitsize="64" type="code_ptr"/>
    <reg name="cpsr" bitsize="32"/>
  </feature>
</target>
"""


@dataclass(slots=True, frozen=True)
class RegisterDescriptor:
    name: str
    width: int


@dataclass(slots=True)
class SoftwareBreakpoint:
    breakpoint_id: int
    address: int
    kind: int
    original_bytes: bytes
    hook_bytes: bytes
    trampoline_addr: int
    armed: bool = True


REGISTERS: tuple[RegisterDescriptor, ...] = tuple(
    [RegisterDescriptor(f"x{i}", 8) for i in range(31)]
    + [RegisterDescriptor("sp", 8), RegisterDescriptor("pc", 8), RegisterDescriptor("cpsr", 4)]
)

BREAKPOINT_MARKER_SLOT = 509
BREAKPOINT_SCRATCH_SLOT = 503
BREAKPOINT_TRAMPOLINE_SLOT_SIZE = 0x40
BREAKPOINT_TRAMPOLINE_BASE_DELTA = 0x800


class AArch64ConcreteGDBTarget:
    architecture = "aarch64"

    def __init__(
        self,
        concrete_device: "ConcreteDevice",
        stepper_factory: Callable[["ConcreteDevice", int], Any] | None = None,
        start_pc: int | None = None,
    ) -> None:
        self.cd = concrete_device
        self._stepper_factory = stepper_factory
        self._current_pc: int | None = None
        self._start_pc: int | None = int(start_pc) if start_pc is not None else None
        self._last_stop = StopReply(signal=5)
        self._breakpoints: dict[int, SoftwareBreakpoint] = {}
        self._pending_breakpoint: int | None = None
        self._next_breakpoint_id = 1

    @property
    def state(self):
        return self.cd.arch_dbg.state

    @property
    def start_pc(self) -> int | None:
        return self._start_pc

    @start_pc.setter
    def start_pc(self, value: int | None) -> None:
        self._start_pc = int(value) if value is not None else None

    def target_xml(self) -> str:
        return TARGET_XML

    def stop_reply(self) -> StopReply:
        self.refresh_stop_state()
        return self._last_stop

    def refresh_stop_state(self, force_pc: bool = False) -> None:
        self.cd.fetch_special_regs()
        inferred_pc = self._infer_pc_from_state()
        if inferred_pc is None:
            inferred_pc = self._fallback_pc_from_state()
        if inferred_pc is not None and (force_pc or self._current_pc is None):
            self._current_pc = inferred_pc

    def read_memory(self, address: int, length: int) -> bytes:
        return self.cd.memdump_region(address, length)

    def write_memory(self, address: int, data: bytes) -> None:
        self.cd.memwrite_region(address, data)

    def read_all_registers(self) -> str:
        self.refresh_stop_state()
        return "".join(self._encode_register(descriptor) for descriptor in REGISTERS)

    def write_all_registers(self, data: str) -> None:
        offset = 0
        dirty_state = False
        for descriptor in REGISTERS:
            chunk_len = descriptor.width * 2
            chunk = data[offset : offset + chunk_len]
            if len(chunk) != chunk_len:
                raise ValueError("register payload length mismatch")
            offset += chunk_len
            dirty_state |= self._write_register_value(descriptor.name, chunk, bulk=True)
        if dirty_state:
            self.cd.sync_state()

    def read_register(self, index: int) -> str:
        descriptor = REGISTERS[index]
        self.refresh_stop_state()
        return self._encode_register(descriptor)

    def write_register(self, index: int, data: str) -> None:
        descriptor = REGISTERS[index]
        dirty_state = self._write_register_value(descriptor.name, data, bulk=False)
        if dirty_state:
            self.cd.sync_state()

    def supports_execution_control(self) -> bool:
        return True

    def supports_software_breakpoints(self) -> bool:
        return True

    def insert_software_breakpoint(self, address: int, kind: int = 4) -> None:
        if address in self._breakpoints:
            return

        breakpoint_id = self._allocate_breakpoint_id()
        trampoline_addr = self._breakpoint_trampoline_addr(breakpoint_id)
        hook_bytes = self._make_breakpoint_hook(trampoline_addr)
        original_bytes = self.cd.memdump_region(address, len(hook_bytes))
        trampoline = self._assemble_breakpoint_trampoline(breakpoint_id, trampoline_addr)

        self.cd.memwrite_region(trampoline_addr, trampoline)
        self.cd.memwrite_region(address, hook_bytes)
        self._breakpoints[address] = SoftwareBreakpoint(
            breakpoint_id=breakpoint_id,
            address=address,
            kind=kind,
            original_bytes=original_bytes,
            hook_bytes=hook_bytes,
            trampoline_addr=trampoline_addr,
            armed=True,
        )

    def remove_software_breakpoint(self, address: int, kind: int = 4) -> None:
        bp = self._breakpoints.pop(address, None)
        if bp is None:
            return
        if bp.armed:
            self.cd.memwrite_region(address, bp.original_bytes)
        if self._pending_breakpoint == address:
            self._pending_breakpoint = None

    def continue_execution(self, address: int | None = None) -> StopReply:
        resume_pc = self._resolve_resume_pc(address)
        resume_pc = self._prepare_resume_from_breakpoint(resume_pc)
        self._clear_breakpoint_marker()

        self.cd.restore_stack_and_jump(resume_pc)
        if self.cd.read(4) != b"GiAs":
            raise ValueError("target did not re-enter the debugger after continue")

        bp = self._detect_breakpoint_hit()
        if bp is not None:
            self._handle_breakpoint_hit(bp)
            return self._last_stop

        self.refresh_stop_state(force_pc=True)
        if self._current_pc is None:
            self._current_pc = resume_pc
        self._last_stop = StopReply(signal=5)
        return self._last_stop

    def step_instruction(self, address: int | None = None) -> StopReply:
        start_pc = self._resolve_resume_pc(address)
        prepared_pc = self._prepare_resume_from_breakpoint(start_pc)
        if prepared_pc != start_pc:
            self._last_stop = StopReply(signal=5)
            return self._last_stop

        stepper = self._create_stepper(prepared_pc)
        stepper.step()
        self._current_pc = int(stepper.pc)
        self._last_stop = StopReply(signal=5)
        return self._last_stop

    def _resolve_resume_pc(self, address: int | None) -> int:
        if address is not None:
            self._current_pc = int(address)
            return self._current_pc

        if self._current_pc is None:
            self.refresh_stop_state()
        if self._current_pc is None:
            raise ValueError("no current PC is available for execution control")
        return int(self._current_pc)

    def _prepare_resume_from_breakpoint(self, resume_pc: int) -> int:
        if self._pending_breakpoint is None:
            return resume_pc

        pending_address = self._pending_breakpoint
        bp = self._breakpoints.get(pending_address)
        if bp is None:
            self._pending_breakpoint = None
            return resume_pc

        if resume_pc == pending_address:
            self._step_over_breakpoint(pending_address)
            return int(self._current_pc)

        self._arm_breakpoint(bp)
        self._pending_breakpoint = None
        return resume_pc

    def _create_stepper(self, pc: int):
        stepper_factory = self._stepper_factory
        if stepper_factory is None:
            from ...archs.arm64.arm64_stepper import ARM64Stepper

            stepper_factory = lambda concrete_device, start_pc: ARM64Stepper(concrete_device, start_pc)
        return stepper_factory(self.cd, pc)

    def _make_breakpoint_hook(self, trampoline_addr: int) -> bytes:
        return self.cd.arch_dbg.sc.branch_absolute(trampoline_addr)

    def _detect_breakpoint_hit(self) -> SoftwareBreakpoint | None:
        breakpoint_id = self._read_breakpoint_marker()
        if breakpoint_id == 0:
            return None

        for bp in self._breakpoints.values():
            if bp.breakpoint_id == breakpoint_id:
                return bp
        raise ValueError(f"unknown breakpoint marker {breakpoint_id:#x}")

    def _handle_breakpoint_hit(self, bp: SoftwareBreakpoint) -> None:
        self._disarm_breakpoint(bp)
        self._clear_breakpoint_marker()
        self._current_pc = bp.address
        self._pending_breakpoint = bp.address
        self._last_stop = StopReply(signal=5, reason="swbreak")

    def _step_over_breakpoint(self, address: int) -> None:
        bp = self._breakpoints.get(address)
        if bp is None:
            raise ValueError(f"no software breakpoint registered at {address:#x}")

        self._disarm_breakpoint(bp)
        stepper = self._create_stepper(address)
        stepper.step()
        self._current_pc = int(stepper.pc)
        self._arm_breakpoint(bp)
        self._pending_breakpoint = None
        self._clear_breakpoint_marker()

    def _arm_breakpoint(self, bp: SoftwareBreakpoint) -> None:
        if bp.armed:
            return
        self.cd.memwrite_region(bp.address, bp.hook_bytes)
        bp.armed = True

    def _disarm_breakpoint(self, bp: SoftwareBreakpoint) -> None:
        if not bp.armed:
            return
        self.cd.memwrite_region(bp.address, bp.original_bytes)
        bp.armed = False

    def _allocate_breakpoint_id(self) -> int:
        breakpoint_id = self._next_breakpoint_id
        self._next_breakpoint_id += 1
        return breakpoint_id

    def _breakpoint_marker_addr(self) -> int:
        return int(self.cd.arch_dbg.storage_addr) + (BREAKPOINT_MARKER_SLOT * 8)

    def _breakpoint_scratch_addr(self) -> int:
        return int(self.cd.arch_dbg.storage_addr) + (BREAKPOINT_SCRATCH_SLOT * 8)

    def _breakpoint_trampoline_addr(self, breakpoint_id: int) -> int:
        stack_base = getattr(self.cd, "ga_stack_location", None)
        if stack_base is None:
            stack_base = int(self.cd.arch_dbg.storage_addr) + 0x1000
        return int(stack_base) + BREAKPOINT_TRAMPOLINE_BASE_DELTA + ((breakpoint_id - 1) * BREAKPOINT_TRAMPOLINE_SLOT_SIZE)

    def _clear_breakpoint_marker(self) -> None:
        self.cd.memwrite_region(self._breakpoint_marker_addr(), struct.pack("<Q", 0))

    def _read_breakpoint_marker(self) -> int:
        return struct.unpack("<Q", self.cd.memdump_region(self._breakpoint_marker_addr(), 8))[0]

    def _assemble_breakpoint_trampoline(self, breakpoint_id: int, trampoline_addr: int) -> bytes:
        assembler = getattr(self.cd.arch_dbg, "ks", None)
        if assembler is None:
            blob = b"BPTR" + struct.pack("<Q", breakpoint_id) + struct.pack("<Q", self.cd.arch_dbg.debugger_addr)
            return blob.ljust(BREAKPOINT_TRAMPOLINE_SLOT_SIZE, b"\x00")

        storage_addr = int(self.cd.arch_dbg.storage_addr)
        debugger_addr = int(self.cd.arch_dbg.debugger_addr)
        scratch_offset = self._breakpoint_scratch_addr() - storage_addr
        marker_offset = self._breakpoint_marker_addr() - storage_addr
        shell = f"""
            ldr x15, STORAGE_addr
            str x0, [x15, #{scratch_offset}]
            mov x0, #{breakpoint_id}
            str x0, [x15, #{marker_offset}]
            ldr x0, [x15, #{scratch_offset}]
            ldr x15, DEBUGGER_addr
            br x15
            DEBUGGER_addr: .quad {hex(debugger_addr)}
            STORAGE_addr: .quad {hex(storage_addr)}
        """
        trampoline = assembler.asm(shell, addr=trampoline_addr, as_bytes=True)[0]
        if len(trampoline) > BREAKPOINT_TRAMPOLINE_SLOT_SIZE:
            raise ValueError("breakpoint trampoline exceeds reserved slot size")
        return trampoline.ljust(BREAKPOINT_TRAMPOLINE_SLOT_SIZE, b"\x00")

    def _encode_register(self, descriptor: RegisterDescriptor) -> str:
        value = self._read_register_value(descriptor.name)
        if value is None:
            return encode_unavailable(descriptor.width)
        return encode_uint_le(value, descriptor.width)

    def _read_register_value(self, name: str) -> int | None:
        if name == "pc":
            return self._current_pc if self._current_pc is not None else self._infer_pc_from_state()
        if name == "cpsr":
            return self._compose_cpsr()
        if name == "sp":
            return int(self.state.SP)
        if name == "x15":
            return None
        if name.startswith("x"):
            return int(getattr(self.state, name.upper()))
        raise KeyError(name)

    def _write_register_value(self, name: str, data: str, *, bulk: bool) -> bool:
        if "x" in data.lower():
            return False

        value = decode_uint_le(data)
        if name == "pc":
            self._current_pc = value
            return False
        if name == "cpsr":
            self.state.NZCV = value & 0xF0000000
            return True
        if name == "sp":
            self.state.SP = value
            return True
        if name == "x15":
            if bulk:
                return False
            raise ValueError("x15 is not writable through the GDB bridge")
        if name.startswith("x"):
            setattr(self.state, name.upper(), value)
            return True
        raise KeyError(name)

    def _compose_cpsr(self) -> int:
        nzcv = int(self.state.NZCV) & 0xFFFFFFFF
        daif = int(getattr(self.state, "DAIF", 0)) & 0xFFFFFFFF
        return nzcv | daif

    def _infer_pc_from_state(self) -> int | None:
        current_el = self.state.R_CURRENT_EL.get_exception_level()
        if current_el == 3:
            value = int(self.state.ELR_EL3)
            return value or None
        if current_el == 2:
            value = int(self.state.ELR_EL2)
            return value or None
        if current_el == 1:
            value = int(self.state.ELR_EL1)
            return value or None
        return None

    def _fallback_pc_from_state(self) -> int | None:
        value = getattr(self.state, "DEBUGGER_JUMP", 0)
        if value:
            return int(value)
        if self._start_pc is not None:
            return self._start_pc
        return None
