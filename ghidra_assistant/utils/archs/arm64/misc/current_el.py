from ....utils import *
from ....bit_helper import BitHelper

class CURRENT_EL(BitHelper):
    '''
    Current EL TODO PROBABLY DOES NOT WORK!!
    https://developer.arm.com/documentation/ddi0601/2020-12/AArch64-Registers/CurrentEL--Current-Exception-Level
    '''
    def __init__(self, value: int) -> None:
        super().__init__(value)

    def get_exception_level(self):
        value = self.get_bits(2, 3)
        if value == '00':
            return 0
        elif value == '01':
            return 1
        elif value == '10':
            return 2
        else:
            #11
            return 3

