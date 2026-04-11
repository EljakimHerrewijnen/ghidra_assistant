import typing
from ...definitions import *
from ...archs.asm_utils import *

if typing.TYPE_CHECKING:
    from concrete_device import ConcreteDevice

class BaseArch_debugger():
    def __init__(self, vector_table_addr, debugger_addr, storage_addr, transmission_size=DEBUGGER_BLOCKSIZE_TRANSMISSION) -> None:
        self.vector_table_addr = vector_table_addr
        self.debugger_addr = debugger_addr
        self.storage_addr = storage_addr
        self.transmission_size=transmission_size
        self.sc = ShellcodeCrafter(None, None)

    def create_debugger_vbar(self) -> bytes:
        raise NotImplementedError()

    def read_vbar(self):
        raise NotImplementedError()

    def write_vbar(self, address):
        raise NotImplementedError()

    def disable_mmu(self):
        '''
        Disable the MMU on the target device.
        '''
        raise NotImplementedError()

    def read_mmu(self):
        '''
        Read sctlr_el3 from the device
        '''
        raise NotImplementedError()

    def enable_mmu(self):
        '''
        Enable the MMU on the target device
        '''
        raise NotImplementedError()

    def write(self, data):
        raise NotImplementedError()

    def read(self, len):
        raise NotImplementedError()

    def get_stub_location(self):
        raise NotImplementedError()

    def ks_to_bytes(self, ks_code):
        return b"".join([int.to_bytes(x, 1, "little") for x in ks_code[0]])

    def _memdump_region_impl(self, mem_param: bytes, size: int, clear_read_size: int | None = None) -> bytes:
        """Shared implementation for PEEK-based memory reads."""
        self.write(b"PEEK")
        self.write(mem_param)

        received = b""
        blk_sz = self.transmission_size
        while len(received) < size:
            if (remaining := size - len(received)) < self.transmission_size:
                blk_sz = remaining
            d = self.read(blk_sz)
            if len(d) == blk_sz:
                self.write(b"ACK\x00")
            received += d

        if size >= self.transmission_size:
            if clear_read_size is not None:
                try:
                    self.read(clear_read_size)
                except Exception:
                    pass
            self.write(b"ACK\x00")

        return received

    def _memwrite_region_impl(self, mem_param: bytes, data: bytes, ok_read_size: int = 2) -> None:
        """Shared implementation for POKE-based memory writes."""
        self.write(b"POKE")
        self.write(mem_param)

        payload = data
        while len(payload) > 0:
            remaining = self.transmission_size
            if len(payload) < self.transmission_size:
                remaining = len(payload)

            send = payload[:remaining]
            payload = payload[remaining:]

            self.write(send)
            message = self.read(ok_read_size)
            if not message.startswith(b"OK"):
                error("Error on writing data to device!")
                return
            self.write(b"ACK\x00")

