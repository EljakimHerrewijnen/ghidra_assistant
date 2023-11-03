from utils.bit_helper import BitHelper
from utils.utils import *

class TCR_ELX(BitHelper):
    def __init__(self, tcr_el3 : int) -> None:
        super().__init__(tcr_el3)

    @property
    def page_size(self):
        raise NotImplemented
    
    @page_size.setter
    def page_size(self, value):
        raise NotImplemented
    
    @property
    def virtual_address_size(self):
        raise NotImplemented
    
    @virtual_address_size.setter
    def virtual_address_size(self, value):
        raise NotImplemented