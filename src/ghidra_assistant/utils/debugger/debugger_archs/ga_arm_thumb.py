import struct
from .base_arch import *
from ...archs.arm.armT_processor_state import ARMThumb_Concrete_State
from ...utils import *

class GA_arm_thumb_debugger(BaseArch_debugger):
    def __init__(self, vector_table_addr, debugger_addr, storage_addr) -> None:
        super().__init__(vector_table_addr, debugger_addr, storage_addr)        
        self.cs = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
        self.ks = Ks(KS_MODE_ARM, KS_MODE_THUMB)
        self.sc = ShellcodeCrafterARMThumb(self.ks, self.cs)
        self.state = ARMThumb_Concrete_State(storage_addr, self)
        
    def memwrite_io(self, address, data):
        assert len(data) < (0x20 - 12), "Data length is too long for IO write"
        self.write("HWIO")
        packet = struct.pack('<III', address, 0, len(data)) + data
        # fill the block up to 0x20 bytes
        packet += b"\x00" * (0x20 - len(packet))
        self.write(packet)
        self.read(self.transmission_size)

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
        blk_sz = self.transmission_size
        while len(received) < size:
            if (remaining := size - len(received)) < self.transmission_size:
                blk_sz = remaining
            d = self.read(blk_sz)
            if len(d) == blk_sz:
                self.write(b"ACK\x00")
            received += d
        if size >= self.transmission_size:
            try:
                # Some USB implementations require a read to clear the buffer??
                self.read(0)
            except:
                pass
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
            remaining = self.transmission_size
            if(len(data) < self.transmission_size):
                remaining = len(data)
            send = data[:remaining]
            data = data[remaining:]
            self.write(send)
            message = self.read(self.transmission_size)
            if(message != b"OK"):
                error("Error on writing data to device!")
                return
            self.write(b"ACK\x00")


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

    def jump_to(self, address):
        '''
        Jump to an absolute address. The bl_shared_data will be provided as first argument (x0)

        Args:

            :param (int): address: Address to where to jump.
        '''
        self.write(b"JUMP")
        self.write(struct.pack("<I", address))

    def add_hook(self, hook_addr, use_smc=True):
        '''
        Adds a hook to the debugger at the specified address
        '''
        return NotImplemented

    def auto_debugger_setup(self):
        '''
        Function that tries to automatically setup the debugger on the device
        '''
        self.debugger_addr = self.get_debugger_location()
        self.state = self.dump_processor_state()
        self.special_regs = self.dump_special_regs()

    def sync_state(self):
        '''
        Sync registers R0-R10 with the values stored in the debugger storage location
        '''
        self.write(b"SYNC")
        if self.read(0x100) != b"GiAs":
            warn("Debugger returned invalid response on syncing state")

    def sync_special_regs(self):
        '''
        Sync special registers from the memory storage location to the actual registers on the device
        '''
        self.write(b"SYNS")
        if self.read(0x100) != b"GiAs":
            warn("Debugger returned invalid response on syncing state")

    def restore_stack_and_jump(self, address, stack : bytes = b""):
        '''
        Restore the saved stack from the memory dump and jump to a user supplied address
        '''
        self.state.DEBUGGER_JUMP = address
        self.write("REST")

    def fetch_special_regs(self):
        self.write(b"SPEC")
        self.read(0x100)

    def write_vbar(self, address):
        return NotImplemented()