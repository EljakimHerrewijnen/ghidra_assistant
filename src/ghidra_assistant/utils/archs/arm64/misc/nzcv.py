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
        Negative condition flag, set if the result of the operation was negative
        '''
        return self.is_set(31)

    @n.setter
    def n(self, value):
        self.set_bit_value(31, value)

    @property
    def z(self):
        '''
        Zero condition flag, set if the result of the operation was zero
        '''
        return self.is_set(30)

    @z.setter
    def z(self, value):
        self.set_bit_value(30, value)

    @property
    def c(self):
        '''
        Carry condition flag, set if the result of the operation was a carry
        '''
        return self.is_set(29)

    @c.setter
    def c(self, value):
        self.set_bit_value(29, value)

    @property
    def v(self):
        '''
        Overflow condition flag, set if the result of the operation was an overflow
        '''
        return self.is_set(28)

    @v.setter
    def v(self, value):
        self.set_bit_value(28, value)

    def __str__(self):
        return f'NZCV: N={int(self.n)} Z={int(self.z)} C={int(self.c)} V={int(self.v)}'

    def condition_met(self, condition: str) -> bool:
        """Evaluate an ARM64 condition code against the current NZCV bits.

        The *condition* parameter should be the mnemonic suffix (e.g. "eq", "ne", "hs").
        Aliases such as "cs"/"hs" are normalised automatically. The result matches the
        semantics defined in Arm ARM (DDI 0601) Table C1-1.
        """
        condition = condition.lower()

        if condition in ("", "al"):  # Always
            return True
        if condition == "nv":  # Historically reserved. Treated as never.
            return False

        checks = {
            "eq": lambda: self.z,
            "ne": lambda: not self.z,
            "cs": lambda: self.c,
            "hs": lambda: self.c,
            "cc": lambda: not self.c,
            "lo": lambda: not self.c,
            "mi": lambda: self.n,
            "pl": lambda: not self.n,
            "vs": lambda: self.v,
            "vc": lambda: not self.v,
            "hi": lambda: self.c and not self.z,
            "ls": lambda: (not self.c) or self.z,
            "ge": lambda: self.n == self.v,
            "lt": lambda: self.n != self.v,
            "gt": lambda: (not self.z) and (self.n == self.v),
            "le": lambda: self.z or (self.n != self.v),
        }

        if condition not in checks:
            raise ValueError(f"Unsupported condition code: {condition}")

        return checks[condition]()