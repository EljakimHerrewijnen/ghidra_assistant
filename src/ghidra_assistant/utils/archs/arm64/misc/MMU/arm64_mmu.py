from .....utils import *
from ..MMU.pagetable_arm64 import PagetableARM64
import math

if typing.TYPE_CHECKING:
    from ...arm64_processor_state import ARM64_Concrete_State

KERNEL_BASE = 0xffff0000_00000000# 0xffffffffc0000000

class ARM64_MMU():
    def __init__(self, state : "ARM64_Concrete_State", kernel_base=KERNEL_BASE) -> None:
        self.state  = state
        self.print_flags = True
        self.print_each_level = False
        self.kernel_base = kernel_base
        # self.el3_ptp =

    def format_entry(self, entry, S2):
        if S2:
            XN = (entry >> 53) & 0b11
            S2AP = (entry >> 6) & 0b11
            A = (entry >> 10) & 0b1
            PhyAddr = entry & 0xfffffffff000

            flags = []

            # Stage 2 - D4-2160
            if XN == 0:
                pass
            elif XN == 1:
                flags += ['PXN']
            elif XN == 2:
                flags += ['UXN','PXN']
            elif XN == 3:
                flags += ['UXN']

            if not A:
                flags += ['!ACC']

            if S2AP == 0:
                flags += ['ELx/NONE']
            elif S2AP == 1:
                flags += ['ELx/RO']
            elif S2AP == 2:
                flags += ['ELx/WO']
            elif S2AP == 3:
                flags += ['ELx/RW']

            flags = " ".join(flags)

            if self.print_flags:
                return "0x%016lx [%s]" % (entry, flags)
            else:
                return "0x%016lx [%s]" % (PhyAddr, flags)
        else:
            XN = (entry >> 53) & 0b11
            AP = (entry >> 6) & 0b11
            NS = (entry >> 5) & 0b1
            A = (entry >> 10) & 0b1
            PhyAddr = entry & 0xfffffffff000

            flags = []

            # D4-2151
            if XN & 1:
                flags += ['PXN']
            if XN & 2:
                flags += ['UXN']

            if NS:
                flags += ['NS']

            if not A:
                flags += ['!ACC']

            if AP == 0:
                flags += ['EL1/RW']
            elif AP == 1:
                flags += ['ELx/RW']
            elif AP == 2:
                flags += ['EL1/RO']
            elif AP == 3:
                flags += ['ELx/RO']

            flags = " ".join(flags)

            if self.print_flags:
                return "0x%016lx [%s]" % (entry, flags)
            else:
                return "0x%016lx [%s]" % (PhyAddr, flags)

    def print_table(self, pt_pa, granule_bits, region_sz, pt_va_base=0, upper_region=False):
        # assuming that the PA range is 47:0 (48-bits)
        stride = granule_bits - 3
        entries_per_table = 2**(stride)
        # round up to the nearest level
        levels = int(math.ceil((64.0 - region_sz - granule_bits)/stride))

        print("Entries/table: %d" % entries_per_table)
        print("Levels: %d" % levels)

        next_lookups = []

        # Table addresses are physical. From the perspective of GDB
        # and depending on if the MMU is enabled, we need to find the
        # corresponding virtual address for the page tables
        tables = [[0, pt_pa]]
        next_tables = []

        if upper_region:
            tables[0][0] = 0xffff000000000000

        # coalesce adjacent entries
        mappings = []

        for level in range(levels):
            if len(tables) == 0:
                break

            last_level = (level+1) == levels

            # Taken straight from D4.2.3 - Memory translation granule size
            x = levels - (level+1) + 3
            lbit = min(47, (x-3)*(stride) + 2*granule_bits-4)
            rbit = granule_bits + (x-3)*(stride)
            bitwidth = lbit - rbit + 1

            if self.print_each_level:
                print("----- LEVEL %d -----" % level)

            for va, table_addr in tables:
                for entry_no in range(entries_per_table):
                    # each entry is 8 bytes
                    entry = self.state.loadQ(pt_va_base + table_addr+entry_no*8)
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

    def invoke(self, CurrentEL : int = -1):
        if CurrentEL == -1: # None given
            CurrentEL = self.debugger.state.CURRENT_EL

        # TODO check if EL is available

        if CurrentEL < 0:
            raise Exception("No paging in el0")
        elif CurrentEL == 1:
            TTBR0_EL1 = self.state.TTBR0_EL1
            TTBR1_EL1 = self.state.TTBR1_EL1
            TCR_EL1 = self.state.TCR_EL1

            # Translation 0 Region Size (usermode)
            T0SZ = TCR_EL1 & 0b111111
            # Translation 1 Region Size (kernel)
            T1SZ = (TCR_EL1 >> 16) & 0b111111
            # Translation 0 Granule Size (user)
            TG0 = (TCR_EL1 >> 14) & 0b11
            # Translation 1 Granule Size (kernel)
            TG1 = (TCR_EL1 >> 30) & 0b11
            IPS = (TCR_EL1 >> 32) & 0b111

            print('IPA Size: %d-bits' % (32+4*IPS))

            if TG0 == 0b00:
                TG0_BITS = 12
            elif TG0 == 0b01:
                TG0_BITS = 16
            elif TG0 == 0b10:
                TG0_BITS = 14
            else:
                print("TG0 reserved")

            if TG1 == 0b01:
                TG1_BITS = 14
            elif TG1 == 0b10:
                TG1_BITS = 12
            elif TG1 == 0b11:
                TG1_BITS = 16
            else:
                print("TG1 reserved")

            print('EL1 Kernel Region Min: 0x%016lx' % (2**64 - 2**(64-T1SZ)))
            print('EL1 Kernel Page Size: %dKB' % (2**TG1_BITS >> 10))
            print('EL1 User Region Max:   0x%016lx' % (2**(64-T0SZ)-1))
            print('EL1 User Page Size: %dKB' % (2**TG0_BITS >> 10))

            print('User Mode Page Tables')
            self.print_table(TTBR0_EL1, TG0_BITS, T0SZ, pt_va_base=self.kernel_base)

            print()
            print('Kernel Mode Page Tables')
            self.print_table(TTBR1_EL1, TG1_BITS, T1SZ, pt_va_base=self.kernel_base,
                    upper_region=True)
        elif CurrentEL == 2:
            VTCR_EL2 = self.state.VTCR_EL2
            VTTBR_EL2 = self.state.VTTBR_EL2

            # Translation 0 Region Size (hypervisor
            T0SZ = VTCR_EL2 & 0b111111
            PA = (VTCR_EL2 >> 16) & 0b11
            TG0 = (VTCR_EL2 >> 14) & 0b11
            SL0 = (VTCR_EL2 >> 6) & 0b11

            if TG0 == 0b00:
                TG0_BITS = 12
            elif TG0 == 0b01:
                TG0_BITS = 16
            elif TG0 == 0b10:
                TG0_BITS = 14
            else:
                print("TG0 reserved")

            print('PA Size: %d-bits' % (32+4*PA))
            print('EL2 Starting Level: %d' % (SL0))
            print('EL2 Region Max: 0x%016lx' % (2**(64-T0SZ)-1))
            print('EL2 Page Size: %dKB' % (2**TG0_BITS >> 10))

            self.print_table(VTTBR_EL2, TG0_BITS, T0SZ)
        elif CurrentEL == 3:
            TTBR0_EL3 = self.state.TTBR0_EL3
            TCR_EL3 = self.state.TCR_EL3

            # Translation 0 Region Size (hypervisor
            T0SZ = TCR_EL3 & 0b111111
            PA = (TCR_EL3 >> 16) & 0b11
            TG0 = (TCR_EL3 >> 14) & 0b11

            if TG0 == 0b00:
                TG0_BITS = 12
            elif TG0 == 0b01:
                TG0_BITS = 16
            elif TG0 == 0b10:
                TG0_BITS = 14
            else:
                print("TG0 reserved")

            print('PA Size: %d-bits' % (32+4*PA))
            print('EL3 Region Max: 0x%016lx' % (2**(64-T0SZ)-1))
            print('EL3 Page Size: %dKB' % (2**TG0_BITS >> 10))

            self.print_table(TTBR0_EL3, TG0_BITS, T0SZ)


    def load_pagetables(self):
        '''
            Loads the pagetables from a running device.
        '''
        self.invoke(1)
        pass
        # self.print_table()
        # self.debugger.state.CURRENT_EL
        # self.el3_pagetables = PagetableARM64(self.debugger, self.debugger.state.TTBR0_EL3, self.debugger.state.R_TCR_EL3.tg0_bits, self.debugger.state.R_TCR_EL3.t0sz)
        # pass