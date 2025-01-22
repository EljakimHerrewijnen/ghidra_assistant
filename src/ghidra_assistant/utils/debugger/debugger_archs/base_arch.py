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

    def create_debugger_vbar() -> bytes:
        return NotImplemented()

    def read_vbar(self):
        return NotImplemented()

    def write_vbar(self, address):
        return NotImplemented()

    def disable_mmu(self):
        '''
        Disable the MMU on the target device.
        '''
        return NotImplemented()

    def read_mmu(self):
        '''
        Read sctlr_el3 from the device
        '''
        return NotImplemented()

    def enable_mmu(self):
        '''
        Enable the MMU on the target device
        '''
        return NotImplemented()
    
    def write(self, data):
        return NotImplemented()

    def read(self, len):
        return NotImplemented()

    def get_stub_location(self):
        return NotImplemented()

    def ks_to_bytes(self, ks_code):
        return b"".join([int.to_bytes(x, 1, "little") for x in ks_code[0]])

