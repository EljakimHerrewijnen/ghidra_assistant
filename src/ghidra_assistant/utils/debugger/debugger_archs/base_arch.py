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
        # Size of the Gupje debugger's per-block POKE acknowledgement ("OK").
        # Part of the generic Gupje protocol; the transport (read/write) is the
        # caller's responsibility.
        self.ok_read_size = 2
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

    def _memdump_region_impl(self, mem_param: bytes, size: int) -> bytes:
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

        # The Gupje PEEK loop is `for (i = 0; i <= size; i += block)`, so when
        # size is an exact multiple of the block size it runs one extra
        # iteration: a zero-byte send (no data) followed by a final ACK round.
        # For non-multiple sizes there is no extra round, so acking here would
        # desync the stream.
        if size > 0 and size % self.transmission_size == 0:
            self.write(b"ACK\x00")

        return received

    def _memwrite_region_impl(self, mem_param: bytes, data: bytes) -> None:
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
            # Gupje acknowledges each written block with "OK"; reply with ACK so
            # the device proceeds to the next block (or returns to its command
            # loop after the last one).
            message = self.read(self.ok_read_size)
            if not message.startswith(b"OK"):
                raise RuntimeError(f"Error writing data to device: expected OK, got {message!r}")
            self.write(b"ACK\x00")

