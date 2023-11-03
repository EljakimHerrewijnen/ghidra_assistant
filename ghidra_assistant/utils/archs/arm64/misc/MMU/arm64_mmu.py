from utils.utils import *
from utils.arm64_misc.MMU.pagetable_arm64 import PagetableARM64

if typing.TYPE_CHECKING:
    from utils.debugger.debugger_archs.ga_arm64 import GA_arm64_debugger

class ARM64_MMU():
    def __init__(self, debugger : "GA_arm64_debugger") -> None:
        self.debugger = debugger
        # self.el3_ptp = 
        
    def load_pagetables(self):
        '''
            Loads the pagetables from a running device.
        '''
        self.el3_pagetables = PagetableARM64(self.debugger, self.debugger.state.TTBR0_EL3, self.debugger.state.R_TCR_EL3.tg0_bits, self.debugger.state.R_TCR_EL3.t0sz)
        pass