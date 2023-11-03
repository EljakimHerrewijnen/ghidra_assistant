from utils.utils import *
from utils.bit_helper import BitHelper

class TTBR0_ELN(BitHelper):
    def __init__(self, ttbr0 : int) -> None:
        super().__init__(ttbr0)

    def base_addr(self, attr):
        '''
        Get bits 1 to 47 from the value
        '''
        return  self.value  & ((1 << 47) - 1)
    
#TODO EL2, EL3
class TTBR0_EL1(TTBR0_ELN):
    '''
    https://developer.arm.com/documentation/ddi0595/2021-06/AArch64-Registers/TTBR0-EL1--Translation-Table-Base-Register-0--EL1-
    '''
    def __init__(self, mair_eln: int) -> None:
        super().__init__(mair_eln)

    