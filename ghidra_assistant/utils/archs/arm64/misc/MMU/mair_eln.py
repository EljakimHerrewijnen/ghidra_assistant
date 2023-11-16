'''
https://developer.arm.com/documentation/ddi0595/2020-12/AArch64-Registers/MAIR-EL3--Memory-Attribute-Indirection-Register--EL3-
https://developer.arm.com/documentation/ddi0601/2021-12/AArch64-Registers/MAIR-EL2--Memory-Attribute-Indirection-Register--EL2-
https://developer.arm.com/documentation/ddi0595/2021-03/AArch64-Registers/MAIR-EL1--Memory-Attribute-Indirection-Register--EL1-
'''

from .....utils import *
from .....bit_helper import BitHelper

class MAIR_ELN(BitHelper):
    def __init__(self, mair_eln : int) -> None:
        super().__init__(mair_eln)
        self.mair_eln = mair_eln

    def get_attribute(self, attr):
        '''
        Get MAIR_ELX attribute. This register is divided into 8 attributes.
        '''
        return (self.value >> (attr * 8)) & 0b11111111

class MAIR_EL3(MAIR_ELN):
    def __init__(self, mair_eln: int) -> None:
        super().__init__(mair_eln)

