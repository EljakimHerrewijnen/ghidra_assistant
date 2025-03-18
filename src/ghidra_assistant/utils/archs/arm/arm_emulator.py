from unicorn.arm_const import *
from unicorn import *
from capstone import *
from keystone import *
from ..asm_utils import ShellcodeCrafter
from ...utils import *

class ARM_Emulator:
    '''
        Class that will interact with the unicorn engine for emulating ARM code.
        Supports both ARM and Thumb modes.
    '''
    def __init__(self, init_uc = True):
        if init_uc:
            self.uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)

        # Disassembler configuration
        self.md = Cs(CS_ARCH_ARM, CS_MODE_ARM)
        self.mdT = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
        self.cs = self.md
        self.csT = self.mdT
        self.ks = Ks(KS_ARCH_ARM, KS_MODE_ARM)
        self.ksT = Ks(KS_ARCH_ARM, KS_MODE_THUMB)
        self.md.detail = True

        self.setup_shellcode()

    def setup_shellcode(self):
        self.sc = ShellcodeCrafter(self.ks, self.cs)
        self.scT = ShellcodeCrafter(self.ksT, self.csT)

    def get_mapping(self, address):
        for mem in self.uc.mem_regions():
            if address >= mem[0] and address < mem[1]:
                return mem
        return None

    def is_mapped(self, address):
        if self.get_mapping(address) != None:
            return True
        return False

    def read_string(self, at):
        if at == 0:
            return b''
        s = b''
        while 1:
            b = self.uc.mem_read(at, 1)
            at += 1
            if b == b'\0':
                return s
            s += b
        return s

    def write_ptr(self, at, ptr):
        return self.uc.mem_write(at, p32(ptr))

    def read_ptr(self, at):
        return u32(self.uc.mem_read(at, 4))

    def add_breakpoint(self, at, target_fun):
        self.uc.hook_add(UC_HOOK_CODE, target_fun, None, at, at + 1)

    def get_registers(self):
        # X0 - X32
        return [self.uc.reg_read(x) for x in [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11, UC_ARM_REG_R12, UC_ARM_REG_R13, UC_ARM_REG_R14, UC_ARM_REG_R15, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC]]

    def disasm(self, address = None, dlen=0x80):
        if not address:
            address = self.pc
        instructions = []
        for instruction in self.md.disasm(self.uc.mem_read(address, dlen), address):
            instructions.append(instruction)
        return instructions

    def print_ctx(self, print_fn=p_info):
        state  = f"""
            PC: 0x{self.PC:8x}\t LR: 0x{self.LR:8x}\t SP: 0x{self.SP:8x}\t FP: 0x{self.FP:8x}\t
            R0: 0x{self.R0:8x}\t R1: 0x{self.R1:8x}\t R2: 0x{self.R2:8x}\t R3: 0x{self.R3:8x}\t
            R4: 0x{self.R4:8x}\t R5: 0x{self.R5:8x}\t R6: 0x{self.R6:8x}\t R7: 0x{self.R7:8x}\t
            R8: 0x{self.R8:8x}\t R9: 0x{self.R9:8x}\tR10: 0x{self.R10:8x}\tR11: 0x{self.R11:8x}\t
            R12: 0x{self.R12:8x}\tR13: 0x{self.R13:8x}\tR14: 0x{self.R14:8x}\tR15: 0x{self.R15:8x}\t
        """
        print_fn(state)

    # ========= Registers =========

    @property
    def pc(self):
        return self.uc.reg_read(UC_ARM_REG_PC)

    @pc.setter
    def pc(self, value):
        self.uc.reg_write(UC_ARM_REG_PC, value)

    @property
    def PC(self):
        return self.uc.reg_read(UC_ARM_REG_PC)

    @PC.setter
    def PC(self, value):
        self.uc.reg_write(UC_ARM_REG_PC, value)

    @property
    def SP(self):
        return self.uc.reg_read(UC_ARM_REG_SP)

    @SP.setter
    def SP(self, value):
        self.uc.reg_write(UC_ARM_REG_SP, value)

    @property
    def LR(self):
        return self.uc.reg_read(UC_ARM_REG_LR)

    @LR.setter
    def LR(self, value):
        self.uc.reg_write(UC_ARM_REG_LR, value)

    @property
    def FP(self):
        return self.uc.reg_read(UC_ARM_REG_R11)

    @FP.setter
    def FP(self, value):
        self.uc.reg_write(UC_ARM_REG_R11, value)

    @property
    def R0(self):
        return self.uc.reg_read(UC_ARM_REG_R0)

    @R0.setter
    def R0(self, value):
        self.uc.reg_write(UC_ARM_REG_R0, value)

    @property
    def R1(self):
        return self.uc.reg_read(UC_ARM_REG_R1)

    @R1.setter
    def R1(self, value):
        self.uc.reg_write(UC_ARM_REG_R1, value)

    @property
    def R2(self):
        return self.uc.reg_read(UC_ARM_REG_R2)

    @R2.setter
    def R2(self, value):
        self.uc.reg_write(UC_ARM_REG_R2, value)

    @property
    def R3(self):
        return self.uc.reg_read(UC_ARM_REG_R3)

    @R3.setter
    def R3(self, value):
        self.uc.reg_write(UC_ARM_REG_R3, value)

    @property
    def R4(self):
        return self.uc.reg_read(UC_ARM_REG_R4)

    @R4.setter
    def R4(self, value):
        self.uc.reg_write(UC_ARM_REG_R4, value)

    @property
    def R5(self):
        return self.uc.reg_read(UC_ARM_REG_R5)

    @R5.setter
    def R5(self, value):
        self.uc.reg_write(UC_ARM_REG_R5, value)

    @property
    def R6(self):
        return self.uc.reg_read(UC_ARM_REG_R6)

    @R6.setter
    def R6(self, value):
        self.uc.reg_write(UC_ARM_REG_R6, value)

    @property
    def R7(self):
        return self.uc.reg_read(UC_ARM_REG_R7)

    @R7.setter
    def R7(self, value):
        self.uc.reg_write(UC_ARM_REG_R7, value)

    @property
    def R8(self):
        return self.uc.reg_read(UC_ARM_REG_R8)

    @R8.setter
    def R8(self, value):
        self.uc.reg_write(UC_ARM_REG_R8, value)

    @property
    def R9(self):
        return self.uc.reg_read(UC_ARM_REG_R9)

    @R9.setter
    def R9(self, value):
        self.uc.reg_write(UC_ARM_REG_R9, value)

    @property
    def R10(self):
        return self.uc.reg_read(UC_ARM_REG_R10)

    @R10.setter
    def R10(self, value):
        self.uc.reg_write(UC_ARM_REG_R10, value)

    @property
    def R11(self):
        return self.uc.reg_read(UC_ARM_REG_R11)

    @R11.setter
    def R11(self, value):
        self.uc.reg_write(UC_ARM_REG_R11, value)

    @property
    def R12(self):
        return self.uc.reg_read(UC_ARM_REG_R12)

    @R12.setter
    def R12(self, value):
        self.uc.reg_write(UC_ARM_REG_R12, value)

    @property
    def R13(self):
        return self.uc.reg_read(UC_ARM_REG_R13)

    @R13.setter
    def R13(self, value):
        self.uc.reg_write(UC_ARM_REG_R13, value)

    @property
    def R14(self):
        return self.uc.reg_read(UC_ARM_REG_R14)

    @R14.setter
    def R14(self, value):
        self.uc.reg_write(UC_ARM_REG_R14, value)

    @property
    def R15(self):
        return self.uc.reg_read(UC_ARM_REG_R15)

    @R15.setter
    def R15(self, value):
        self.uc.reg_write(UC_ARM_REG_R15, value)

    @property
    def cpsr(self):
        return self.uc.reg_read(UC_ARM_REG_CPSR)

    @cpsr.setter
    def cpsr(self, value):
        self.uc.reg_write(UC_ARM_REG_CPSR, value)

    @property
    def spsr(self):
        return self.uc.reg_read(UC_ARM_REG_SPSR)

    @spsr.setter
    def spsr(self, value):
        self.uc.reg_write(UC_ARM_REG_SPSR, value)

    @property
    def zf(self):
        return self.cpsr & 0x40000000

    @zf.setter
    def zf(self, value):
        if value:
            self.cpsr |= 0x40000000
        else:
            self.cpsr &= ~0x40000000

    @property
    def is_thumb(self) -> bool:
        return self.cpsr & 0x20 != 0

    @is_thumb.setter
    def is_thumb(self, value):
        if value:
            self.cpsr |= 0x20 # Set the thumb bit
        else:
            self.cpsr &= ~0x20 # Clear the thumb bit