from enum import Enum
from utils.utils import *
from utils.bit_helper import BitHelper
from utils.arm64_misc.tcr_el.tcr_el3 import TCR_EL3

EL3_LVL0_CONTIG_BIT     = 53
EL3_LVL0_PXN_BIT        = 54
EL3_LVL0_UXN_BIT        = 55
EL3_LVL0_NG_BIT         = 12
EL3_LVL0_AF_BIT         = 11
EL3_LVL0_NS_BIT         = 6

class MemoryType(Enum):
    '''
    https://developer.arm.com/documentation/den0024/a/Memory-Ordering/Memory-types/Device-memory
    '''
    NORMAL  = 3
    BLOCK   = 0
    UNKNOWN = 0xff

class ARM64_PTE(BitHelper):
    ''' 
    https://developer.arm.com/documentation/102416/0100/Single-level-table-at-EL3
    https://github.com/grant-h/gdbscripts/blob/master/aarch64/aarch64-pagewalk.py
    https://developer.arm.com/documentation/102376/0100/Describing-the-memory-type
    https://developer.arm.com/documentation/ddi0601/2021-12/AArch64-Registers/TCR-EL3--Translation-Control-Register--EL3-?lang=en#fieldset_0-13_12

    TODO

    '''
    def __init__(self, pte : int, tcr_el3 = 32) -> None:
        super().__init__(pte)
        if type(tcr_el3) == TCR_EL3:
            self.tcr_el3 = tcr_el3
        else:
            self.tcr_el3 = TCR_EL3(tcr_el3)

        self.unused_end = (pte >> 59 & 0b1111)
        self.reserved_hw = (pte >> 55 & 0b1111)
        # self.sh = (pte >> 9 & 0b11)
        self.indx = (pte >> 3 & 0b111)
        self.memory_type_bits = (pte >> 0 & 0b11) # previously undefined start

    @property
    def sh(self):
        '''
        Shareability attribute for memory associated with translation table walks using TTBR0_EL3.

        0b00 | Non-shareable.
        0b10 | Outer Shareable.
        0b11 | Inner Shareable.

        Other values are reserved. The effect of programming this field to a Reserved value is that behavior is CONSTRAINED UNPREDICTABLE.

        The reset behavior of this field is:

            On a Warm reset, this field resets to an architecturally UNKNOWN value.
        '''
        return (self.value >> 9 & 0b11)
    
    @sh.setter
    def sh(self, value):
        if value == 0:
            # Non shareable
            self.clear_bit(10)
            self.clear_bit(11)
        elif value == 1:
            warn("Invalid shareability bits, this is reserved")
            self.clear_bit(10)
            self.set_bit(11)
        elif value == 2:
            # Outer shareable
            self.set_bit(10)
            self.clear_bit(11)
        else:
            # 3 Inner Shareable
            self.set_bit(10)
            self.set_bit(11)

    @property
    def ap(self):
        '''
        https://developer.arm.com/documentation/den0024/a/The-Memory-Management-Unit/Access-permissions
        AP	Unprivileged (EL0)	Privileged (EL1/2/3)
        00	No access	Read and write
        01	Read and write	Read and write
        10	No access	Read-only
        11	Read-only	Read-only
        
        '''
        return self.get_bits(7, 8)
    
    @ap.setter
    def ap(self, value):
        if value == 0:
            # 00
            self.clear_bit(7)
            self.clear_bit(8)
        elif value == 1:
            # 01
            self.clear_bit(7)
            self.set_bit(8)
        elif value == 2:
            # 10
            self.set_bit(7)
            self.clear_bit(8)
        elif value == 3:
            # 11
            self.set_bit(7)
            self.set_bit(8)
        else:
            warn("Invalid R/W access passed, setting to 0")
            self.clear_bit(7)
            self.clear_bit(8)

    @property
    def ns(self):
        '''
        When 0, the page is only accessible by Secure world, with 1 accessible by all.
        '''
        return self.is_set(EL3_LVL0_NS_BIT)
    
    @ns.setter
    def ns(self, value):
        if value == 0:
            self.clear_bit(EL3_LVL0_NS_BIT)
        else:
            self.set_bit(EL3_LVL0_NS_BIT)

    @property
    def af(self):
        '''
        When 0, the entry is not part of a contiguous block
        '''
        return self.is_set(EL3_LVL0_AF_BIT)
    
    @af.setter
    def af(self, value):
        if value == 0:
            self.clear_bit(EL3_LVL0_AF_BIT)
        else:
            self.set_bit(EL3_LVL0_AF_BIT)

    @property
    def ng(self):
        '''
        Not used at EL3
        '''
        return self.is_set(EL3_LVL0_NG_BIT)
    
    @ng.setter
    def ng(self, value):
        if value == 0:
            self.clear_bit(EL3_LVL0_NG_BIT)
        else:
            self.set_bit(EL3_LVL0_NG_BIT)

    @property
    def contig(self):
        '''
        When 0, the entry is not part of a contiguous block
        '''
        return self.is_set(EL3_LVL0_CONTIG_BIT)
    
    @contig.setter
    def contig(self, value):
        if value == 0:
            self.clear_bit(EL3_LVL0_CONTIG_BIT)
        else:
            self.set_bit(EL3_LVL0_CONTIG_BIT)
    
    @property
    def uxn(self):
        '''
        Not used in EL3
        '''
        return self.is_set(EL3_LVL0_UXN_BIT)
    
    @uxn.setter
    def uxn(self, value):
        if value == 0:
            self.clear_bit(EL3_LVL0_UXN_BIT)
        else:
            self.set_bit(EL3_LVL0_UXN_BIT)

    @property
    def pxn(self):
        '''
        Page eXecute Never. When set to 1 this page can never be executed. 
        '''
        return self.is_set(EL3_LVL0_PXN_BIT)
    
    @pxn.setter
    def pxn(self, value):
        if value == 0:
            self.clear_bit(EL3_LVL0_PXN_BIT)
        else:
            self.set_bit(EL3_LVL0_PXN_BIT)

    @property
    def pfn(self):
        '''
        PFN: Page file number. Depending on the granularity size this can be calculated into an address. E.g 4KB pagesize means PFN * 0x1000 for the physicall address.
        '''
        return (self.value >> 12 & 0b111111111111111111111111111111111111111)
    
        # TODO TEST
        return (self.value >> 12 & 0b111111111111111111111111111111111111111000000000000 >> 12)
        return (self.value & 0b111111111111111111111111111111111111111000000000000) >> 12
    
        self.value = (self.value & ~0b111111111111111111111111111111111111111000000000000) | (x << 12)
        0x7FFFFFFFFF000
    
    @pfn.setter
    def pfn(self, pfn_value):
        # this value must be the correct value, not the absolute address. See the PFN documentation

        # Prepare the new value to be written (ensure it fits within 25 bits)
        pfn_value &= 0x1FFFFFF  # Mask the new value to 25 bits (bits 24 to 0)

        # Clear bits 36 to 12 in the original number
        clear_mask = ~((0xFFF << 12) | 0xFFFFFFFFF000)
        cleared_number = self.value & clear_mask

        # Shift the new value to align with bits 36 to 12
        shifted_new_value = pfn_value << 12

        # Combine the new value with the cleared original number
        self.value = cleared_number | shifted_new_value
    
    @property
    def memory_type(self):
        if self.memory_type_bits == 3:
            return MemoryType.NORMAL
        elif self.memory_type_bits == 1:
            return MemoryType.BLOCK
        return MemoryType.UNKNOWN



    @property
    def address(self):
        '''
        Get the physical address of a PTE. This address is calculated by using the PFN * the granule size(usually 4KB)
        '''
        return self.pfn * self.tcr_el3.page_size
    
    @address.setter
    def address(self, value):
        self.pfn = value // self.tcr_el3.page_size    
    
    def print_header(self):
        print(f"{COLOR_RED}+---------------------------------------------------------------------------------+{COLOR_END}")
        print(f"{COLOR_LBLUE}|63 : 59|58:55|54 |53 |52 |   51 : 12    |11|10|9:8|7:6|5 |4:2 |1:0|--------------+{COLOR_END}")
        print(f"{COLOR_RED}+---------------------------------------------------------------------------------+{COLOR_END}")
        print(f"{COLOR_LBLUE}|       |RESER|UXN|PXN|CON|     PFN      |nG|AF|SH |AP |NS|Indx|   |  ADDRESS     |{COLOR_END}")

    def print_entry(self, print_header=False):
        print(f"{COLOR_GREEN}+---------------------------------------------------------------------------------+{COLOR_END}")
        if print_header:
            self.print_header()
        print(f"{COLOR_LBLUE}| {self.get_bits(59, 63)} |{self.get_bits(55, 58)} | {int(self.uxn)} | {int(self.pxn)} | {int(self.contig)} |{self.pretty_print_value(self.pfn)}|{int(self.ng)} |{int(self.af)} | {self.sh} | {self.ap} |{int(self.ns)} |{self.get_bits(2, 4)} |{self.get_bits(0,1)} |{self.pretty_print_value(hex(self.address))}|{COLOR_END}")

    