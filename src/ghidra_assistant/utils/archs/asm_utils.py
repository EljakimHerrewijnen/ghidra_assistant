from dis import Instruction
from keystone import *
from capstone import *
from ...utils.utils import *
import io

# cs_64 = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
# ks_64 = Ks(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN)
# cs_32 = Cs(CS_ARCH_ARM, CS_MODE_ARM)
# ks_32 = Ks(KS_ARCH_ARM, KS_MODE_ARM)
# cs_t = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
# ks_t = Ks(KS_ARCH_ARM, KS_MODE_THUMB)

def bytes_to_c_pat(d):
    d_rev = bytes(reversed(d))
    return ', '.join(reversed([ '0x' + d_rev[i:i+4].hex() for i in range(0, len(d_rev), 4) ]))

def ks_to_bytes(ks_code):
    return b"".join([int.to_bytes(x, 1, "little") for x in ks_code[0]])

class ShellcodeCrafter():
    def __init__(self, cs, ks) -> None:
        self.instruction_size = 4

    def fill_with_nops(self, shellcode, length):
        return NotImplemented()

    def branch_patch(self, offset, address):
        return NotImplemented()

    def branch_absolute(self, address, register = "x24"):
        return NotImplemented()

    def disasm_bytes(self, code, offset=0, include_offset=True):
        '''
        disasssemble with capstone bytearray. Provide offset if necessary
        '''
        res = []
        try:
            for i in range(0, len(code), self.instruction_size):
                dis = list(self.cs.disasm(code[i:i+self.instruction_size], offset=offset + i))
                if len(dis) > 0:
                    res.append(dis)
                else:
                    res.append(code[i:i+self.instruction_size])
        except Exception as e:
            error(e)
            return "Disassembly failed!"
        ret = ""
        count = 0
        for ins in res:
            if include_offset:
                ret += f"[{hex(offset + count * self.instruction_size)}] "
            if type(ins) == bytes:
                ret += f"{ins.hex()}\n"
            else:
                ins = ins[0]
                ret += ins.mnemonic + " " + ins.op_str + "\n"
            count += 1
        return ret

    def disasm_ks(self, code, offset):
        '''
        Disassemble with capstone an object from keystone
        '''
        c = ks_to_bytes(code)
        return self.disasm_bytes(c, offset)

    def set_bit(self, value, bit):
        return value | (1<<bit)

    def clear_bit(self, value, bit):
        return value & ~(1<<bit)

class ShellcodeCrafterARMThumb(ShellcodeCrafter):
    def __init__(self, assembler, disassembler) -> None:
        if assembler is None:
            assembler = ks_t
        if disassembler is None:
            disassembler = cs_t
        self.ks = assembler
        self.cs = disassembler
        self.instruction_size = 2

        # predefined instructions
        self.nop_ins = ks_to_bytes(self.ks.asm("nop"))

