from ..asm_utils import *

class ShellcodeCrafterARM64(ShellcodeCrafter):
    def __init__(self, assembler, disassembler) -> None:
        if assembler is None:
            assembler = Ks(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN)
        if disassembler is None:
            disassembler = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
        self.ks = assembler
        self.cs = disassembler
        self.instruction_size = 4

        #predefined instructions
        self.nop_ins = ks_to_bytes(self.ks.asm("NOP"))
        self.smc_ins = ks_to_bytes(self.ks.asm("SMC #0x7777"))
        self.mov_0_w0_ins = ks_to_bytes(self.ks.asm("MOV w0, #0"))
        self.mov_0_w1_ins = ks_to_bytes(self.ks.asm("MOV w1, #0"))
        self.mov_2_w0_ins = ks_to_bytes(self.ks.asm("MOV w0, #2"))
        self.mov_1_w0_ins = ks_to_bytes(self.ks.asm("MOV w0, #2"))
        self.eret_ins = ks_to_bytes(self.ks.asm("ERET"))
        self.ret_ins = ks_to_bytes(self.ks.asm("RET"))

    def fill_with_nops(self, shellcode, length):
        if(length % 4 != 0):
            error("Invalid instruction length!")
            return
        if(len(shellcode) == 0):
            return length // len(self.nop_ins) * self.nop_ins
        rest = length - len(shellcode)
        out = shellcode + ((rest // len(shellcode)) * self.nop_ins)
        return out

    def branch_patch(self, offset, address):
        '''
        Create a branch instruction that will branch to an address based of an offset:
        input:
            offset = address of the instruction you want to patch. We need this because ARM only branches to relative offsets
            address = actual address you want to branch to.
        result:
            bl #address     | (based on ofset)
        '''
        shellcode = f"b #{hex(address)}"
        code = self.ks.asm(shellcode, addr=offset, as_bytes=True)[0]
        return code

    def branch_absolute(self, address, register = "x15", branch_ins="blr"):
        '''
        For doing an absolute branch in ARM.
        Creates a shellcode blob that will load the target address into the supplied register and branch to it.
        '''
        shell = f"""
            ldr {register}, JUMP_addr
            {branch_ins} {register}
            JUMP_addr:           .quad {hex(address)}
        """
        return self.ks.asm(shell, as_bytes=True)[0]

    def branch_absolute_minimal(self, address, register = "x24"):
        #TODO add branch to this code, but that will only use 3 instructions. This kan be done with mov and movk
        return NotImplemented()