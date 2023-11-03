'''
This file will be deprecated in favor of the MMU!
'''

from utils.utils import *
from utils.bit_helper import BitHelper
from utils.arm64_misc.tcr_el.tcr_el3 import TCR_EL3
from utils.arm64_misc.MMU.arm64_pte import ARM64_PTE
import math

if typing.TYPE_CHECKING:
    from utils.debugger.debugger_archs.ga_arm64 import GA_arm64_debugger

class PagetableARM64():
    '''
    granule_size    = tg0_bits      tg_bits
    region_size     = t0_sz         tsz

    https://armv8-ref.codingbelief.com/en/chapter_d4/d42_3_memory_translation_granule_size.html
    https://github.com/grant-h/gdbscripts.git
    https://github.com/ashwio/arm64-pgtable-tool.git
    '''
    def load_entry(self, addr):
        return self.debugger.loadQ(addr) & 0xfffffff000
    
    def Pagewalk(self, ttbr, tcr):
        if ttbr % 0x1000 != 0:
            warn(f"TTBR_ELX : Not page aligned: {hex(ttbr)}")
            return



    def print_all_entries_in_ptp(self, ptp_dump):
        if (len(ptp_dump) % 8) != 0:
            warn("Invalid PTP dump!")
            return
        for i in range(len(ptp_dump) // 8):
            pte = ARM64_PTE(u64(ptp_dump[i * 8: (i* 8) + 8]))
            pte.print_entry()

    
    def __init__(self, debugger : "GA_arm64_debugger", ptp_pa, granule_size, region_sz, page_size = 0x1000, pt_va_base=0, upper_region=False) -> None:
        '''
            Pagetable managment on ARM64

            REMOVEME
            granule_bits = granule_size

        '''
        self.tsz = region_sz
        self.tg_bits = granule_size
        self.pt_va_base = pt_va_base
        self.upper_region = upper_region

        self.debugger = debugger    # For interacting with the device
        self.ptp_pa = ptp_pa        # base address of the pagetable
        self.va_space_bits = self.tsz
        self.va_size = 2**(64-self.va_space_bits) # t0sz
        self.ptp_size = 2**granule_size
        self.ptp_entries = self.ptp_size // 8   # Entry is always 8 bytes.
        self.va_size // self.ptp_size
        
        # assuming that the PA range is 47:0 (48-bits)
        self.table_idx_bits = int(math.log(self.ptp_entries, 2)) #stride
        self.block_offset_bits = int(math.log(granule_size, 2)) 

        self.start_level = 3 - (self.tsz - self.block_offset_bits) // self.table_idx_bits
        if (self.tsz - self.block_offset_bits) % self.table_idx_bits == 0:
            self.start_level = self.start_level + 1
            info(f"start_level corrected as {self.tsz} exactly fits in first table")

        # Calculate max amount of levels
        self.levels = int(math.ceil((64.0 - region_sz - granule_size)/self.table_idx_bits))

        # index tables locally        
        self.tables = [[0, ptp_pa]]
        # self.next_tables = []
        if self.upper_region:
            self.tables[0][0] = 0xffff000000000000

        # coalesce adjacent entries
        self.mappings = []


        # Walk through the tables
        for level in range(self.levels):
            if len(self.tables) == 0:
                break

            is_last_level = (level+1) == self.levels # Bool is last_level

            # Taken straight from D4.2.3 - Memory translation granule size
            x = self.levels - (level+1) + self.block_offset_bits

            lbit = min(self.va_space_bits, (x-3)*(self.table_idx_bits) + 2 * self.tg_bits -4)
            rbit = self.tg_bits + (x-3)*(self.table_idx_bits)
            bitwidth = lbit - rbit + 1

            ok(f"----- LEVEL {level} -----")
            for va, table_addr in self.tables:
                for entry_no in range(self.ptp_entries):
                    entry = self.load_entry(pt_va_base + table_addr + entry_no * 8) # Will result in a PTE
                    pte_entry = ARM64_PTE(entry)
                    
                    # TODO add sanity check for each PTE

                    if pte_entry.memory_type_bits == 3:
                        # Next table entry. 
                        info(f"PAGETABLE: pte_entry.address")
                        self.tables += [[new_va, (entry & 0xfffffff000)]]
                        # if is_last_level:
                        #     self.mappings += [[new_va, pte_entry]]
                    elif pte_entry.memory_type_bits == 1:
                        # Block device
                        info(f"BLOCKDEV: pte_entry.address")



        # Table addresses are physical. From the perspective of GDB
        # and depending on if the MMU is enabled, we need to find the
        # corresponding virtual address for the page tables

        # coalesce adjacent entries
        mappings = []

        for level in range(levels):

            for va, table_addr in tables:
                for entry_no in range(entries_per_table):
                    # each entry is 8 bytes
                    entry = self.loadq(pt_va_base + table_addr+entry_no*8)
                    new_va = va | (entry_no << rbit)

                    # next table entry
                    if (entry & 0b11) == 3:
                        if last_level:
                            if self.print_each_level:
                                print("%016lx: %s" % (new_va, self.format_entry(entry, False)))
                            mappings += [[new_va, self.format_entry(entry, False)]]
                        else:
                            if self.print_each_level:
                                print("%016lx: %016lx" % (new_va, entry))
                            next_tables += [[new_va, (entry & 0xfffffff000)]]
                    # block entry
                    elif (entry & 0b11) == 1:
                        if self.print_each_level:
                            print("%016lx: %s" % (new_va, self.format_entry(entry, False)))
                        mappings += [[new_va, self.format_entry(entry, False)]]

            tables = next_tables
            next_tables = []

        if len(mappings):
            for m in mappings:
                print("%016lx: %s" % (m[0], m[1]))
        else:
            print("No virtual mappings found")
    
'''
WILL PROBABLY BE DEPRECATED!!
'''
class PagetableARM64_el3:
    def __init__(self, dump : bytes = b"", level=0) -> None:
        self.dump = dump
        self.level = level
        self.entries = []

    def auto_build_ptp(self, cd : "ConcreteDevice"):
        # self.print_table(TTBR0_EL3, TG0_BITS, T0SZ)
        # TG0_BITS = cd.arch_dbg.state.R_TCR_EL3.tg0_bits = granule_bits
        # T0SZ = cd.arch_dbg.state.R_TCR_EL3.tg0sz = region_sz

        # assuming that the PA range is 47:0 (48-bits)
        stride = cd.arch_dbg.state.R_TCR_EL3.tg0_bits - 3
        entries_per_table = 2**(stride)
        # round up to the nearest level
        levels = int(math.ceil((64.0 - cd.arch_dbg.state.R_TCR_EL3.t0sz - cd.arch_dbg.state.R_TCR_EL3.tg0_bits) / stride))
        for level in range(levels):
            pass
        pass

    def parse_ptp(self):
        '''
            Parse pagetable page from dump
        '''
        if len(self.dump) % 0x1000 != 0:
            warn("unalligned PTP dump")
        for i in range(0, len(self.dump), 8):
            if self.level == 0:
                pte = ARM64_PTE(int.from_bytes(self.dump[i:i+8], 'little'))
                self.entries.append(pte)
            else:
                raise NotImplemented
            
    def print_entries(self):
        self.entries[0].print_header()
        for pte in self.entries:
            pte.print_entry(False)

    def remove_pxn_all_entries(self):
        for pte in self.entries:
            pte.pxn = 0
            # pte.uxn = 0

    def set_ns_bit_entries(self):
        '''
        Sets NS bit to 1, meaning all accesses are granted for secure and non secure
        '''
        for pte in self.entries:
            pte.ns = 1

    def make_all_pages_rw(self):
        for pte in self.entries:
            pte.ap = 0
            # pte.uxn = 0

    def entries_to_pagetabledump(self):
        ret = b""
        for pte in self.entries:
            ret += struct.pack("<Q", pte.value)
        return ret