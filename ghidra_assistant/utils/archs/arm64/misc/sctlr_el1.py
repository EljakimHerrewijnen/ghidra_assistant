from utils.utils import *
from utils.bit_helper import BitHelper

MMU_SCTLR_EL1       = 0
A_SCTLR_EL1         = 1
C_SCTLR_EL1         = 2

class SCTLR_EL1(BitHelper):
    '''
    INCOMPLETE!!

    System Control Register for EL1
    https://developer.arm.com/documentation/ddi0595/2021-12/AArch64-Registers/SCTLR-EL1--System-Control-Register--EL1-
    '''
    def __init__(self, value: int) -> None:
        super().__init__(value)

    @property
    def mmu(self):
        '''
        0: EL1 stage 1 address translation disabled.
        1: EL1 stage 1 address translation enabled.
        '''
        return self.is_set(MMU_SCTLR_EL1)

    @mmu.setter
    def mmu(self, value):
        self.set_bit_value(MMU_SCTLR_EL1, value)

    @property
    def a(self):
        '''
        Alignment
        0:	Alignment fault checking disabled when executing at EL1.
            Instructions that load or store one or more registers, other than load/store exclusive and load-acquire/store-release, do not check that the address being accessed is aligned to the size of the data element(s) being accessed.

        1: Alignment fault checking enabled when executing at EL1.
            All instructions that load or store one or more registers have an alignment check that the address being accessed is aligned to the size of the data element(s) being accessed. If this check fails it causes an Alignment fault, which is taken as a Data Abort exception.
        '''
        return self.is_set(A_SCTLR_EL1)

    @a.setter
    def a(self, value):
        self.set_bit_value(A_SCTLR_EL1, value)

    @property
    def c(self):
        '''
        Cacheability ??
        0: All data access to Normal memory from EL1, and all Normal memory accesses to the EL1 translation tables, are Non-cacheable for all levels of data and unified cache.
        '''
        return self.is_set(C_SCTLR_EL1)

    @c.setter
    def c(self, value):
        self.set_bit_value(C_SCTLR_EL1, value)