from ....utils import *
from ....bit_helper import BitHelper

TME_SCTLR_EL3       = 53
TMT_SCTLR_EL3       = 51
DSSBS_SCTLR_EL3     = 44
MMU_SCTLR_EL3       = 0
A_SCTLR_EL3         = 1
C_SCTLR_EL3         = 2
WXN_SCTLR_EL3       = 19

class SCTLR_EL3(BitHelper):
    '''
    System Control Register for EL3
    https://developer.arm.com/documentation/ddi0500/e/system-control/aarch64-register-descriptions/system-control-register--el3
    '''
    def __init__(self, value: int) -> None:
        super().__init__(value)
        
    @property
    def dssbs(self):
        '''
        if FEAT_DSSBS
            Enables the Data Speculation Barrier at EL3.
        '''
        return self.is_set(DSSBS_SCTLR_EL3)
    
    @dssbs.setter
    def dssbs(self, value):
        self.set_bit_value(DSSBS_SCTLR_EL3, value)
        
    @property
    def tmt(self):
        '''
        if FEAT_TMT
            Enables the Topology Modification Table at EL3.
        '''
        return self.is_set(TMT_SCTLR_EL3)
    
    @tmt.setter
    def tmt(self, value):
        self.set_bit_value(TMT_SCTLR_EL3, value)
        
    @property
    def bp(self):
        '''
        if FEAT_BP
            Enables the Branch Prediction at EL3.
        '''
        return self.is_set(TMT_SCTLR_EL3)
    
    @bp.setter
    def bp(self, value):
        self.set_bit_value(TMT_SCTLR_EL3, value)

    @property
    def tme(self):
        '''
        if FEAT_TME
            Enables the Transactional Memory Extension at EL3.
        '''
        return self.is_set(TME_SCTLR_EL3)

    @tme.setter
    def tme(self, value):
        self.set_bit_value(TME_SCTLR_EL3, value)

    @property
    def mmu(self):
        '''
        0: EL3 stage 1 address translation disabled.
        1: EL3 stage 1 address translation enabled.
        '''
        return self.is_set(MMU_SCTLR_EL3)

    @mmu.setter
    def mmu(self, value):
        self.set_bit_value(MMU_SCTLR_EL3, value)

    @property
    def a(self):
        '''
        Alignment
        0:	Alignment fault checking disabled when executing at EL3.
            Instructions that load or store one or more registers, other than load/store exclusive and load-acquire/store-release, do not check that the address being accessed is aligned to the size of the data element(s) being accessed.

        1: Alignment fault checking enabled when executing at EL3.
            All instructions that load or store one or more registers have an alignment check that the address being accessed is aligned to the size of the data element(s) being accessed. If this check fails it causes an Alignment fault, which is taken as a Data Abort exception.
        '''
        return self.is_set(A_SCTLR_EL3)

    @a.setter
    def a(self, value):
        self.set_bit_value(A_SCTLR_EL3, value)

    @property
    def c(self):
        '''
        Cacheability
        0: All data access to Normal memory from EL3, and all Normal memory accesses to the EL3 translation tables, are Non-cacheable for all levels of data and unified cache.
        '''
        return self.is_set(C_SCTLR_EL3)

    @c.setter
    def c(self, value):
        self.set_bit_value(C_SCTLR_EL3, value)

    @property
    def wxn(self):
        '''
        Write eXecute Never:
        0: No effect
        1: Any region that is writable in the EL3 translation regime is forced to XN for accesses from software executing at EL3.
        '''
        return self.is_set(WXN_SCTLR_EL3)

    @wxn.setter
    def wxn(self, value):
        self.set_bit_value(WXN_SCTLR_EL3, value)
