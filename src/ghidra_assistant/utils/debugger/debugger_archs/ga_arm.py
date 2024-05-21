import struct
from ...debugger.debugger_archs.base_arch import *
from ...utils import *

if typing.TYPE_CHECKING:
    from concrete_device import ConcreteDevice

class GA_arm_debugger(BaseArch_debugger):
    def __init__(self, concrete_device="ConreteDevice") -> None:
        super().__init__()

    def memdump_region(self, offset, size):
        '''
        Dump a region from target device. Based on an offset/address and size:

        Args:

            :param offset: Address of which to dump
            :param size: Size to dump

        Returns:

            Bytes
        '''
        self.write(b"PEEK")
        mem_param = struct.pack('<III', offset, size, 0) #Send extra 4 bytes to fill the 12 byte buffer
        self.write(mem_param)
        received = b''
        blk_sz = DEBUGGER_BLOCKSIZE_TRANSMISSION
        while len(received) < size:
            if (remaining := size - len(received)) < DEBUGGER_BLOCKSIZE_TRANSMISSION:
                blk_sz = remaining
            d = self.read(blk_sz)
            if len(d) == blk_sz:
                self.write(b"ACK\x00")
            received += d
        if size >= DEBUGGER_BLOCKSIZE_TRANSMISSION:
            self.write(b"ACK\x00")
        return received

    def memwrite_region(self, address, data):
        '''
        Write a blob of data to an address on the device.

        Args:

            :param (int): address: Address to write to
            :param (bytes): data: Binary data to write to the device
            :param (Bool): check if data is really written by dumping the region and checking if it has changed
        '''
        size = len(data)
        self.write(b"POKE")
        mem_param = struct.pack('<III', address, size, 0) #Send extra 4 bytes to fill the 12 byte buffer
        self.write(mem_param)

        while len(data) > 0:
            remaining = 0x200
            if(len(data) < 0x200):
                remaining = len(data)
            send = data[:remaining]
            data = data[remaining:]
            self.write(send)
            message = self.read(0x3ff)
            if(message != b"OK"):
                error("Error on writing data to device!")
                return
            self.write(b"ACK\x00")

    def get_debugger_location(self):
        self.write(b"SELF")
        d = self.read(DEBUGGER_BLOCKSIZE_TRANSMISSION)
        return struct.unpack("<I", d)[0]

    def disable_mmu(self):
        return NotImplemented()

    def read_mmu(self):
        return NotImplemented()

    def enable_mmu(self):
        return NotImplemented()

    def read_vbar(self):
        return NotImplemented()

    def send_verify_cmd(self, cmd):
        return NotImplemented()

    def write_vbar(self, address):
        return NotImplemented()