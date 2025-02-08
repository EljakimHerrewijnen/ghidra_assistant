from ....utils import *
from ....bit_helper import BitHelper

class NZCV_Register(BitHelper):
    '''
    Processor status flags
    https://developer.arm.com/documentation/ddi0601/2024-12/AArch64-Registers/NZCV--Condition-Flags
    '''
    def __init__(self, value: int) -> None:
        super().__init__(value)
        
    @property
    def n(self):
        '''
        Negative condition flag
        '''
        return self.is_set(31)
    
    @n.setter
    def n(self, value):
        self.set_bit_value(31, value)
        
    @property
    def z(self):
        '''
        Zero condition flag
        '''
        return self.is_set(30)
    
    @z.setter
    def z(self, value):
        self.set_bit_value(30, value)
        
    @property
    def c(self):
        '''
        Carry condition flag
        '''
        return self.is_set(29)
    
    @c.setter
    def c(self, value):
        self.set_bit_value(29, value)
        
    @property
    def v(self):
        '''
        Overflow condition flag
        '''
        return self.is_set(28)
    
    @v.setter
    def v(self, value):
        self.set_bit_value(28, value)
        
        