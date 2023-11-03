class BitHelper:
    def __init__(self, value : int) -> None:
        self.value = value
        
    def is_set(self, bit):
        return self.value & 1 << bit != 0
    
    def set_bit(self, bit):
        self.value = self.value | (1<<bit)

    def clear_bit(self, bit):
        self.value = self.value & ~(1<<bit)
    
    def set_bit_value(self, bit, value):
        if value == 0:
            self.clear_bit(bit)
        else:
            self.set_bit(bit)
    
    def get_bits(self, start, end):
        ret = ""
        for i in range(start, end + 1, 1):
            if self.is_set(i):
                ret += "1"
            else:
                ret += "0"
        return ret
    
    def pretty_print_value(self, value, line_len = 14):
        '''
        Prints a value in the middle of the line, depending on the user supplied length
        '''
        pfn_len = len(str(value))
        div_len = ((line_len - pfn_len) // 2)
        ret = (div_len * " ") + str(value)
        ret += (line_len  - len(ret) ) * " "
        return ret

    def get_mask(self, start: int, end: int) -> int:
        """
        Bitmask from bit 'start' to 'end' - excludes bit 'end'.
        """
        assert start < end, f"start must be before end, was {start=} {end=}"
        # create a string of (end - start) 1 bits and shift it left by 'start' bits
        return ((1 << (end - start)) - 1) << start

    def read_bits(self, value: int, start: int, end: int) -> int:
        """
        Returns the value between bit 'start' and 'end' as an integer.
        """
        return (value & self.get_mask(start, end)) >> start

    def pack_bits(self, base: int, value: int, start: int, end: int) -> int:
        """
        Returns 'base', with the section between 'start' and 'end' set to 'value'.
        Raises ValueError if value is too large.
        """
        mask = self.get_mask(start, end)

        if (value << start) & ~mask:
            raise ValueError(f"Value {value} doesn't fit between bits {start} and {end}")

        return (base & ~mask) | ((value << start) & mask)
