from ....bit_helper import BitHelper

class CURRENT_EL(BitHelper):
    '''
    Current exception level helper.
    Bits [3:2] of CurrentEL encode the active EL.
    '''
    def __init__(self, value: int) -> None:
        super().__init__(value)

    def get_exception_level(self) -> int:
        return self.read_bits(self.value, 2, 4)

