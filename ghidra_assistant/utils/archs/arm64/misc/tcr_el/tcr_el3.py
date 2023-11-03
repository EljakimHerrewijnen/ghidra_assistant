from utils.utils import *
from utils.arm64_misc.tcr_el.tcr_elx import TCR_ELX


TCR_EL3_DS          = 32
TCR_EL3_RES0        = 31
TCR_EL3_TCMA        = 30
TCR_EL3_TBID        = 29
TCR_EL3_HWU62       = 28
TCR_EL3_HWU61       = 27
TCR_EL3_HWU60       = 26
TCR_EL3_HWU59       = 25
TCR_EL3_HPD         = 24
TCR_EL3_HD          = 22
TCR_EL3_HA          = 21
TCR_EL3_TBI         = 20

class TCR_EL3(TCR_ELX):
    #  https://developer.arm.com/documentation/ddi0601/2021-12/AArch64-Registers/TCR-EL3--Translation-Control-Register--EL3-?lang=en
    def __init__(self, tcr_el3 : int) -> None:
        super().__init__(tcr_el3)
        self.tcr_el3 = tcr_el3

        if self.tg0 == 0b00:
            self.tg0_bits = 12
        elif self.tg0 == 0b01:
            self.tg0_bits = 16
        elif self.tg0 == 0b10:
            self.tg0_bits = 14
        else:
            info("TG0 reserved")
    
    @property
    def tcma(self):
        '''
        when FEAT_MTE2 is enabled:
            Controls generation of unchecked addresses at EL3. When set to 1 all accesses are unchecked.
        otherwise:
            reserved
        '''
        return self.is_set(TCR_EL3_TCMA)
    
    @tcma.setter
    def tcma(self, value):
        self.set_bit_value(TCR_EL3_TCMA, value)

    @property
    def tbid(self):
        '''
        when FEAT_PAuth is enabled:
            Controls generation of unchecked addresses at EL3. When set to 1 all accesses are unchecked.
        otherwise:
            reserved
        '''
        return self.is_set(TCR_EL3_TBID)
    
    @tcma.setter
    def tbid(self, value):
        self.set_bit_value(TCR_EL3_TBID, value)

    @property
    def hwu62(self):
        '''
        '''
        return self.is_set(TCR_EL3_HWU62)
    
    @hwu62.setter
    def hwu61(self, value):
        self.set_bit_value(TCR_EL3_HWU62, value)

    @property
    def hwu61(self):
        '''
        '''
        return self.is_set(TCR_EL3_HWU61)
    
    @hwu61.setter
    def hwu61(self, value):
        self.set_bit_value(TCR_EL3_HWU61, value)

    @property
    def hwu60(self):
        '''
        '''
        return self.is_set(TCR_EL3_HWU60)
    
    @hwu60.setter
    def hwu60(self, value):
        self.set_bit_value(TCR_EL3_HWU60, value)

    @property
    def hwu59(self):
        '''
        '''
        return self.is_set(TCR_EL3_HWU59)
    
    @hwu59.setter
    def hwu59(self, value):
        self.set_bit_value(TCR_EL3_HWU59, value)

    @property
    def hpd(self):
        '''
        Disables hierarchical permissions This affects the hierarchical control bits, APTable, PXNTable, and UXNTable, except NSTable, in the translation tables pointed to by TTBR0_EL3.
        When set to 1 the permissions are disabled.
        '''
        return self.is_set(TCR_EL3_HPD)
    
    @hpd.setter
    def hpd(self, value):
        self.set_bit_value(TCR_EL3_HPD, value)

    @property
    def hd(self):
        '''

        '''
        return self.is_set(TCR_EL3_HD)
    
    @hd.setter
    def hd(self, value):
        self.set_bit_value(TCR_EL3_HD, value)

    @property
    def ha(self):
        '''
        '''
        return self.is_set(TCR_EL3_HA)
    
    @ha.setter
    def ha(self, value):
        self.set_bit_value(TCR_EL3_HA, value)

    @property
    def ds(self):
        '''
        '''
        return self.is_set(TCR_EL3_DS)
    
    @ds.setter
    def ds(self, value):
        self.set_bit_value(TCR_EL3_DS, value)

    @property
    def tbi(self):
        '''
        When set to 1 the top byte is ignored for address calculation on TTBR0_EL3
        '''
        return self.is_set(TCR_EL3_TBI)
    
    @tbi.setter
    def tbi(self, value):
        self.set_bit_value(TCR_EL3_TBI, value)

    @property
    def ps(self):
        return (self.value >> 16) & 0b111
    
    @ps.setter
    def ps(self, value):
        raise NotImplemented
    
    @property
    def pagesize_bits(self):
        return (32+4*self.ps)
    
    @property
    def tg0(self):
        return (self.value >> 14) & 0b11
    
    @tg0.setter
    def tg0(self, value):
        raise NotImplemented
    
    # @property
    # def granularity(self):
    #     val = (self.value >> 14 & 0b11)
    #     if val == 0b0:
    #         return 0x1000 #4Kb
    #     elif val == 0b01:
    #         return 0x10000 #64Kb
    #     else:
    #         #0b10
    #         return 0x4000 #16Kb
        
    # @granularity.setter
    # def granularity(self, value):
    #     raise NotImplemented
    
    @property
    def sh0(self):
        '''
        Shareability attribute associated with translation walks from ttbr0_el3
        '''
        return self.get_bits(12, 13)

    @sh0.setter
    def sh0(self, value):
        raise NotImplemented
    
    @property
    def orgn0(self):
        '''
        '''
        return self.get_bits(10, 11)

    @orgn0.setter
    def orgn0(self, value):
        raise NotImplemented
    
    @property
    def irgn0(self):
        '''
        '''
        return self.get_bits(8, 9)

    @irgn0.setter
    def irgn0(self, value):
        raise NotImplemented
    
    @property
    def t0sz(self):
        '''
        '''
        return self.value & 0b111111
        # return self.get_bits(0, 5) 

    @t0sz.setter
    def t0sz(self, value):
        raise NotImplemented
    
    @property
    def translation_size(self):
        return 2 ** (64 - (self.value >> 5 & 0b11111))
    
    @translation_size.setter
    def translation_size(self, value):
        raise NotImplemented
    
    @property
    def virtual_address_size(self):
        return 2**(64-self.t0sz)
    
    @virtual_address_size.setter
    def virtual_address_size(self, value):
        raise NotImplemented
    
    @property
    def page_size(self):
        return (2**self.tg0_bits >> 10) * KB
    
    @page_size.setter
    def page_size(self, value):
        raise NotImplemented
    
    @property
    def max_size(self):
        return (2**(64-self.t0sz)-1)