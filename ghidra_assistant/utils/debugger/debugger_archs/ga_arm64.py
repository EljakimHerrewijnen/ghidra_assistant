import struct
from ...bit_helper import BitHelper
from ...archs.arm64.arm64_processor_state import ARM64_Concrete_State
from ...debugger.debugger_archs.base_arch import *
from ...utils import *
from ...archs.arm64.asm_arm64 import ShellcodeCrafterARM64
from keystone import *
from capstone import *

cs_64 = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
ks_64 = Ks(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN)

ARM64_MMU_ENABLED_BIT = 0
GA_ARM64_PROCESSOR_DUMP_SIZE    = 32 * 8
GA_ARM64_SPECIAL_REG_SIZE       = 21 * 8

class GA_arm64_debugger(BaseArch_debugger):
    '''
        This debugger acts as the host command requester for the target device. This will implement basic code for peeking and poking addresses, which can then be used to setup a full debugger.
        It also handles the architecture specific commands.
    '''
    def __init__(self, vector_table_addr, debugger_addr, storage_addr) -> None:
        super().__init__(vector_table_addr, debugger_addr, storage_addr)
        self.cs = cs_64
        self.ks = ks_64
        self.sc = ShellcodeCrafterARM64(self.ks, self.cs)
        self.vbar_el3_hijacked = 0x0
        self.vbar_el3_original = 0x146a9000
        self.state = ARM64_Concrete_State(storage_addr, self)

    def loadQ(self, address):
        return u64(self.memdump_region(address, 8))

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
        mem_param = struct.pack('<QI', offset, size)
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
        # if size >= DEBUGGER_BLOCKSIZE_TRANSMISSION:
        #     self.write(b"ACK\x00")
        #     received += self.read(DEBUGGER_BLOCKSIZE_TRANSMISSION)
        return received

    def memdump_region_small(self, offset, size):
        '''
        Dump a region from target device. Based on an offset/address and size:
        Size = 4

        Args:

            :param offset: Address of which to dump
            :param size: Size to dump

        Returns:

            Bytes
        '''
        self.write(b"PEKS")
        mem_param = struct.pack('<QI', offset, size)
        self.write(mem_param)
        received = b''
        blk_sz = 4
        while len(received) < size:
            if (remaining := size - len(received)) < 4:
                blk_sz = remaining
            d = self.read(blk_sz)
            if len(d) == blk_sz:
                self.write(b"ACK\x00")
            received += d
        if size >= 4:
            self.write(b"ACK\x00")
            received += self.read(4)
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
        mem_param = struct.pack('<QI', address, size)
        self.write(mem_param)

        while len(data) > 0:
            remaining = DEBUGGER_BLOCKSIZE_TRANSMISSION
            if(len(data) < DEBUGGER_BLOCKSIZE_TRANSMISSION):
                remaining = len(data)
            send = data[:remaining]
            data = data[remaining:]
            self.write(send)
            message = self.read(DEBUGGER_BLOCKSIZE_TRANSMISSION)
            if(message != b"OK"):
                error("Error on writing data to device!")
                return
            self.write(b"ACK\x00")

    def restore_and_jump(self, address : int):
        self.state.DEBUGGER_JUMP = struct.pack("<Q", address)
        self.write(b"REST")

    def get_debugger_location(self):
        self.write(b"SELF")
        d = self.read(DEBUGGER_BLOCKSIZE_TRANSMISSION)
        return struct.unpack("<Q", d)[0]

    def create_debugger_vbar(self, register="X15"):
        '''
        Creates branches to the debugger and stores the exception ID. By default X15 is corrupted.
        '''
        if(self.vector_table_addr % 0x800 != 0):
            error("Address not 2k alligned")

        vbar = b""
        exception_id = 0
        for i in range(0, 0x800, 0x80):
            # Fill remaining instructions with NOPs
            if len(vbar) < i:
                remaining = (i - len(vbar))
                if remaining % 4 != 0:
                    error("Failure on creating VBAR")
                    return b""
                vbar += self.sc.nop_ins * (remaining // 4)

            # Write identifier for the exception ID
            id_shell = f'''
                ldr {register}, STORAGE_addr
                STR X0, [X15, #4072]
                MOV X0, #{hex(exception_id)}

                STR X0, [X15, #4080]
                LDR X0, [X15, #4072]
                NOP

                ldr {register}, JUMP_addr
                BR {register}
                JUMP_addr:              .quad {hex(self.debugger_addr)}
                STORAGE_addr:           .quad {hex(self.storage_addr)}
            '''
            vbar += self.sc.ks.asm(id_shell, as_bytes=True)[0]
            exception_id += 1

        if len(vbar) < 0x800:
            remaining = (0x800 - len(vbar))
            if remaining % 4 != 0:
                error("Failure on creating VBAR")
                return b""
            vbar += self.sc.nop_ins * (remaining // 4)
        return vbar

    def jump_to(self, address):
        '''
        Jump to an absolute address. The bl_shared_data will be provided as first argument (x0)

        Args:

            :param (int): address: Address to where to jump.
        '''
        self.write(b"JUMP")
        self.write(struct.pack("<Q", address))

    def add_hook(self, hook_addr, use_smc=True):
        '''
        Adds a hook to the debugger at the specified address
        '''
        if use_smc:
            raise NotImplemented
        else:
            #Add absolute branch to debugger
            self.memwrite_region(hook_addr, self.sc.branch_absolute(self.debugger_addr))

    def auto_debugger_setup(self):
        '''
        Function that tries to automatically setup the debugger on the device
        '''
        self.debugger_addr = self.get_debugger_location()
        self.state = self.dump_processor_state()
        self.special_regs = self.dump_special_regs()

    def sync_state(self):
        '''
        Sync registers x0-x28 with the values stored in the debugger storage location
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

    def disable_mmu(self, el = 3):
        '''
        Disable the MMU on the target device.
        '''
        if el == 3:
            self.state.SCTLR_EL3 = self.sc.clear_bit(self.state.SCTLR_EL3, ARM64_MMU_ENABLED_BIT)
            if not self.state.auto_sync_special:
                self.sync_special_regs()
        elif el == 1:
            self.state.SCTLR_EL1 = self.sc.clear_bit(self.state.SCTLR_EL1, ARM64_MMU_ENABLED_BIT)
            if not self.state.auto_sync_special:
                self.sync_special_regs()
        else:
            return NotImplemented

    def enable_mmu(self, el = 3):
        '''
        Enable the MMU on the target device.
        '''
        if el == 3:
            self.state.SCTLR_EL3 = self.sc.set_bit(self.state.SCTLR_EL3, ARM64_MMU_ENABLED_BIT)
            if not self.state.auto_sync_special:
                self.sync_special_regs()
        elif el == 1:
            self.state.SCTLR_EL1 = self.sc.set_bit(self.state.SCTLR_EL1, ARM64_MMU_ENABLED_BIT)
            if not self.state.auto_sync_special:
                self.sync_special_regs()
        else:
            return NotImplemented

    def continue_execution(self, exception_id=-1):
        '''
        Continue original execution flow.

        TODO save the original VBAR
        '''
        if exception_id == -1:
            exception_id =  self.state.EXCEPTION_ID
        self.restore_stack_and_jump(self.vbar_el3_original + (0x80 * exception_id))
        pass

    def fetch_special_regs(self):
        self.write(b"SPEC")
        self.read(0x100)