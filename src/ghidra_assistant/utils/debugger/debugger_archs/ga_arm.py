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
        mem_param = struct.pack('<III', offset, size, 0) #Send extra 4 bytes to fill the 12 byte buffer
        return self._memdump_region_impl(mem_param, size)

    def memwrite_region(self, address, data):
        '''
        Write a blob of data to an address on the device.

        Args:

            :param (int): address: Address to write to
            :param (bytes): data: Binary data to write to the device
            :param (Bool): check if data is really written by dumping the region and checking if it has changed
        '''
        size = len(data)
        mem_param = struct.pack('<III', address, size, 0) #Send extra 4 bytes to fill the 12 byte buffer
        self._memwrite_region_impl(mem_param, data)

    def get_debugger_location(self):
        self.write(b"SELF")
        d = self.read(self.transmission_size)
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