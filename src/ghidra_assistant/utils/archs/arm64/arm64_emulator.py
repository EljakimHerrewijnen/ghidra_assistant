from unicorn.arm64_const import *
from unicorn import *
from capstone import *
from keystone import *
from ..asm_utils import ShellcodeCrafter
from ...utils import *

class ARM64UC_Emulator():
    def __init__(self, init_uc = True) -> None:
        super().__init__()

        if init_uc:
            self.uc = Uc(UC_ARCH_ARM64, UC_MODE_LITTLE_ENDIAN)

        # Disassembler configuration
        self.md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
        self.cs = self.md
        self.ks = Ks(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN)
        self.md.detail = True

        self.setup_shellcode()

    def setup_shellcode(self):
        self.sc = ShellcodeCrafter(self.ks, self.cs)

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
        return [self.uc.reg_read(x) for x in [UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2, UC_ARM64_REG_X3, UC_ARM64_REG_X4, UC_ARM64_REG_X5, UC_ARM64_REG_X6, UC_ARM64_REG_X7, UC_ARM64_REG_X8, UC_ARM64_REG_X9, UC_ARM64_REG_X10, UC_ARM64_REG_X11, UC_ARM64_REG_X12, UC_ARM64_REG_X13, UC_ARM64_REG_X14, UC_ARM64_REG_X15, UC_ARM64_REG_X16, UC_ARM64_REG_X17, UC_ARM64_REG_X18, UC_ARM64_REG_X19, UC_ARM64_REG_X20, UC_ARM64_REG_X21, UC_ARM64_REG_X22, UC_ARM64_REG_X23, UC_ARM64_REG_X24, UC_ARM64_REG_X25, UC_ARM64_REG_X26, UC_ARM64_REG_X27, UC_ARM64_REG_X28, UC_ARM64_REG_X29, UC_ARM64_REG_X30, UC_ARM64_REG_PC]]

    def disasm(self, address = None, dlen=0x80):
        if not address:
            address = self.pc
        instructions = []
        for instruction in self.md.disasm(self.uc.mem_read(address, dlen), address):
            instructions.append(instruction)
        return instructions

    def print_ctx(self, print_f = info):
        pc = self.uc.reg_read(UC_ARM64_REG_PC)
        sp = self.uc.reg_read(UC_ARM64_REG_SP)
        lr = self.uc.reg_read(UC_ARM64_REG_LR)
        regs = self.get_registers()

        print_f("  x0 : 0x{0:016X}      x1 : 0x{1:016X}      x2 : 0x{2:016X}      x3 : 0x{3:016X}".format(*regs[0:4]))
        print_f("  x4 : 0x{0:016X}      x5 : 0x{1:016X}      x6 : 0x{2:016X}      x7 : 0x{3:016X}".format(*regs[4:8]))
        print_f("  x8 : 0x{0:016X}      x9 : 0x{1:016X}     x10 : 0x{2:016X}     x11 : 0x{3:016X}".format(*regs[8:12]))
        print_f(" x12 : 0x{0:016X}     x13 : 0x{1:016X}     x14 : 0x{2:016X}     x15 : 0x{3:016X}".format(*regs[12:16]))
        print_f(" x16 : 0x{0:016X}     x17 : 0x{1:016X}     x18 : 0x{2:016X}     x19 : 0x{3:016X}".format(*regs[16:20]))
        print_f(" x20 : 0x{0:016X}     x21 : 0x{1:016X}     x22 : 0x{2:016X}     x23 : 0x{3:016X}".format(*regs[20:24]))
        print_f(" x24 : 0x{0:016X}     x25 : 0x{1:016X}     x26 : 0x{2:016X}     x27 : 0x{3:016X}".format(*regs[24:28]))
        print_f(" x28 : 0x{0:016X}     x29 : 0x{1:016X}     x30 : 0x{2:016X}     pc  : 0x{3:016X}".format(*regs[28:32]))
        print_f("  SP : 0x{0:016X}      LR : 0x{1:016X}".format(sp, lr))
        instruction = None
        try:
            insn = self.disasm(pc)[0]
            instruction = '{}\t{}'.format(insn.mnemonic, insn.op_str)
        except:
            instruction = '???'
        print_f("IP {:016x} :::: {}".format(pc, instruction))
        #hexdump(self.uc.mem_read(pc, 0x10))

    @property
    def pc(self):
        return self.uc.reg_read(UC_ARM64_REG_PC)

    @pc.setter
    def pc(self, value):
        self.uc.reg_write(UC_ARM64_REG_PC, value)

    @property
    def sp(self):
        return self.uc.reg_read(UC_ARM64_REG_SP)

    @sp.setter
    def sp(self, value):
        self.uc.reg_write(UC_ARM64_REG_SP, value)

    @property
    def lr(self):
        return self.uc.reg_read(UC_ARM64_REG_LR)

    @lr.setter
    def lr(self, value):
        self.uc.reg_write(UC_ARM64_REG_LR, value)

    @property
    def vbar_el1(self):
        return self.uc.reg_read(UC_ARM64_REG_VBAR_EL1)

    @vbar_el1.setter
    def vbar_el1(self, value):
        self.uc.reg_write(UC_ARM64_REG_VBAR_EL1, value)

    @property
    def vbar_el2(self):
        return self.uc.reg_read(UC_ARM64_REG_VBAR_EL2)

    @vbar_el2.setter
    def vbar_el2(self, value):
        self.uc.reg_write(UC_ARM64_REG_VBAR_EL2, value)

    @property
    def vbar_el3(self):
        return self.uc.reg_read(UC_ARM64_REG_VBAR_EL3)

    @vbar_el3.setter
    def vbar_el3(self, value):
        self.uc.reg_write(UC_ARM64_REG_VBAR_EL3, value)

    @property
    def elr_el0(self):
        return self.uc.reg_read(UC_ARM64_REG_ELR_EL0)

    @elr_el0.setter
    def elr_el0(self, value):
        self.uc.reg_write(UC_ARM64_REG_ELR_EL0, value)

    @property
    def elr_el1(self):
        return self.uc.reg_read(UC_ARM64_REG_ELR_EL1)

    @elr_el1.setter
    def elr_el1(self, value):
        self.uc.reg_write(UC_ARM64_REG_ELR_EL1, value)

    @property
    def elr_el2(self):
        return self.uc.reg_read(UC_ARM64_REG_ELR_EL2)

    @elr_el2.setter
    def elr_el2(self, value):
        self.uc.reg_write(UC_ARM64_REG_ELR_EL2, value)

    @property
    def elr_el3(self):
        return self.uc.reg_read(UC_ARM64_REG_ELR_EL3)

    @elr_el3.setter
    def elr_el3(self, value):
        self.uc.reg_write(UC_ARM64_REG_ELR_EL3, value)

#======== Auto generated ========

    @property
    def X0(self):
        return self.uc.reg_read(UC_ARM64_REG_X0)

    @X0.setter
    def X0(self, value):
        self.uc.reg_write(UC_ARM64_REG_X0, value)


    @property
    def W0(self):
        return self.uc.reg_read(UC_ARM64_REG_W0)

    @W0.setter
    def W0(self, value):
        self.uc.reg_write(UC_ARM64_REG_W0, value)


    @property
    def X1(self):
        return self.uc.reg_read(UC_ARM64_REG_X1)

    @X1.setter
    def X1(self, value):
        self.uc.reg_write(UC_ARM64_REG_X1, value)


    @property
    def W1(self):
        return self.uc.reg_read(UC_ARM64_REG_W1)

    @W1.setter
    def W1(self, value):
        self.uc.reg_write(UC_ARM64_REG_W1, value)


    @property
    def X2(self):
        return self.uc.reg_read(UC_ARM64_REG_X2)

    @X2.setter
    def X2(self, value):
        self.uc.reg_write(UC_ARM64_REG_X2, value)


    @property
    def W2(self):
        return self.uc.reg_read(UC_ARM64_REG_W2)

    @W2.setter
    def W2(self, value):
        self.uc.reg_write(UC_ARM64_REG_W2, value)


    @property
    def X3(self):
        return self.uc.reg_read(UC_ARM64_REG_X3)

    @X3.setter
    def X3(self, value):
        self.uc.reg_write(UC_ARM64_REG_X3, value)


    @property
    def W3(self):
        return self.uc.reg_read(UC_ARM64_REG_W3)

    @W3.setter
    def W3(self, value):
        self.uc.reg_write(UC_ARM64_REG_W3, value)


    @property
    def X4(self):
        return self.uc.reg_read(UC_ARM64_REG_X4)

    @X4.setter
    def X4(self, value):
        self.uc.reg_write(UC_ARM64_REG_X4, value)


    @property
    def W4(self):
        return self.uc.reg_read(UC_ARM64_REG_W4)

    @W4.setter
    def W4(self, value):
        self.uc.reg_write(UC_ARM64_REG_W4, value)


    @property
    def X5(self):
        return self.uc.reg_read(UC_ARM64_REG_X5)

    @X5.setter
    def X5(self, value):
        self.uc.reg_write(UC_ARM64_REG_X5, value)


    @property
    def W5(self):
        return self.uc.reg_read(UC_ARM64_REG_W5)

    @W5.setter
    def W5(self, value):
        self.uc.reg_write(UC_ARM64_REG_W5, value)


    @property
    def X6(self):
        return self.uc.reg_read(UC_ARM64_REG_X6)

    @X6.setter
    def X6(self, value):
        self.uc.reg_write(UC_ARM64_REG_X6, value)


    @property
    def W6(self):
        return self.uc.reg_read(UC_ARM64_REG_W6)

    @W6.setter
    def W6(self, value):
        self.uc.reg_write(UC_ARM64_REG_W6, value)


    @property
    def X7(self):
        return self.uc.reg_read(UC_ARM64_REG_X7)

    @X7.setter
    def X7(self, value):
        self.uc.reg_write(UC_ARM64_REG_X7, value)


    @property
    def W7(self):
        return self.uc.reg_read(UC_ARM64_REG_W7)

    @W7.setter
    def W7(self, value):
        self.uc.reg_write(UC_ARM64_REG_W7, value)


    @property
    def X8(self):
        return self.uc.reg_read(UC_ARM64_REG_X8)

    @X8.setter
    def X8(self, value):
        self.uc.reg_write(UC_ARM64_REG_X8, value)


    @property
    def W8(self):
        return self.uc.reg_read(UC_ARM64_REG_W8)

    @W8.setter
    def W8(self, value):
        self.uc.reg_write(UC_ARM64_REG_W8, value)


    @property
    def X9(self):
        return self.uc.reg_read(UC_ARM64_REG_X9)

    @X9.setter
    def X9(self, value):
        self.uc.reg_write(UC_ARM64_REG_X9, value)


    @property
    def W9(self):
        return self.uc.reg_read(UC_ARM64_REG_W9)

    @W9.setter
    def W9(self, value):
        self.uc.reg_write(UC_ARM64_REG_W9, value)


    @property
    def X10(self):
        return self.uc.reg_read(UC_ARM64_REG_X10)

    @X10.setter
    def X10(self, value):
        self.uc.reg_write(UC_ARM64_REG_X10, value)


    @property
    def W10(self):
        return self.uc.reg_read(UC_ARM64_REG_W10)

    @W10.setter
    def W10(self, value):
        self.uc.reg_write(UC_ARM64_REG_W10, value)


    @property
    def X11(self):
        return self.uc.reg_read(UC_ARM64_REG_X11)

    @X11.setter
    def X11(self, value):
        self.uc.reg_write(UC_ARM64_REG_X11, value)


    @property
    def W11(self):
        return self.uc.reg_read(UC_ARM64_REG_W11)

    @W11.setter
    def W11(self, value):
        self.uc.reg_write(UC_ARM64_REG_W11, value)


    @property
    def X12(self):
        return self.uc.reg_read(UC_ARM64_REG_X12)

    @X12.setter
    def X12(self, value):
        self.uc.reg_write(UC_ARM64_REG_X12, value)


    @property
    def W12(self):
        return self.uc.reg_read(UC_ARM64_REG_W12)

    @W12.setter
    def W12(self, value):
        self.uc.reg_write(UC_ARM64_REG_W12, value)


    @property
    def X13(self):
        return self.uc.reg_read(UC_ARM64_REG_X13)

    @X13.setter
    def X13(self, value):
        self.uc.reg_write(UC_ARM64_REG_X13, value)


    @property
    def W13(self):
        return self.uc.reg_read(UC_ARM64_REG_W13)

    @W13.setter
    def W13(self, value):
        self.uc.reg_write(UC_ARM64_REG_W13, value)


    @property
    def X14(self):
        return self.uc.reg_read(UC_ARM64_REG_X14)

    @X14.setter
    def X14(self, value):
        self.uc.reg_write(UC_ARM64_REG_X14, value)


    @property
    def W14(self):
        return self.uc.reg_read(UC_ARM64_REG_W14)

    @W14.setter
    def W14(self, value):
        self.uc.reg_write(UC_ARM64_REG_W14, value)


    @property
    def X15(self):
        return self.uc.reg_read(UC_ARM64_REG_X15)

    @X15.setter
    def X15(self, value):
        self.uc.reg_write(UC_ARM64_REG_X15, value)


    @property
    def W15(self):
        return self.uc.reg_read(UC_ARM64_REG_W15)

    @W15.setter
    def W15(self, value):
        self.uc.reg_write(UC_ARM64_REG_W15, value)


    @property
    def X16(self):
        return self.uc.reg_read(UC_ARM64_REG_X16)

    @X16.setter
    def X16(self, value):
        self.uc.reg_write(UC_ARM64_REG_X16, value)


    @property
    def W16(self):
        return self.uc.reg_read(UC_ARM64_REG_W16)

    @W16.setter
    def W16(self, value):
        self.uc.reg_write(UC_ARM64_REG_W16, value)


    @property
    def X17(self):
        return self.uc.reg_read(UC_ARM64_REG_X17)

    @X17.setter
    def X17(self, value):
        self.uc.reg_write(UC_ARM64_REG_X17, value)


    @property
    def W17(self):
        return self.uc.reg_read(UC_ARM64_REG_W17)

    @W17.setter
    def W17(self, value):
        self.uc.reg_write(UC_ARM64_REG_W17, value)


    @property
    def X18(self):
        return self.uc.reg_read(UC_ARM64_REG_X18)

    @X18.setter
    def X18(self, value):
        self.uc.reg_write(UC_ARM64_REG_X18, value)


    @property
    def W18(self):
        return self.uc.reg_read(UC_ARM64_REG_W18)

    @W18.setter
    def W18(self, value):
        self.uc.reg_write(UC_ARM64_REG_W18, value)


    @property
    def X19(self):
        return self.uc.reg_read(UC_ARM64_REG_X19)

    @X19.setter
    def X19(self, value):
        self.uc.reg_write(UC_ARM64_REG_X19, value)


    @property
    def W19(self):
        return self.uc.reg_read(UC_ARM64_REG_W19)

    @W19.setter
    def W19(self, value):
        self.uc.reg_write(UC_ARM64_REG_W19, value)


    @property
    def X20(self):
        return self.uc.reg_read(UC_ARM64_REG_X20)

    @X20.setter
    def X20(self, value):
        self.uc.reg_write(UC_ARM64_REG_X20, value)


    @property
    def W20(self):
        return self.uc.reg_read(UC_ARM64_REG_W20)

    @W20.setter
    def W20(self, value):
        self.uc.reg_write(UC_ARM64_REG_W20, value)


    @property
    def X21(self):
        return self.uc.reg_read(UC_ARM64_REG_X21)

    @X21.setter
    def X21(self, value):
        self.uc.reg_write(UC_ARM64_REG_X21, value)


    @property
    def W21(self):
        return self.uc.reg_read(UC_ARM64_REG_W21)

    @W21.setter
    def W21(self, value):
        self.uc.reg_write(UC_ARM64_REG_W21, value)


    @property
    def X22(self):
        return self.uc.reg_read(UC_ARM64_REG_X22)

    @X22.setter
    def X22(self, value):
        self.uc.reg_write(UC_ARM64_REG_X22, value)


    @property
    def W22(self):
        return self.uc.reg_read(UC_ARM64_REG_W22)

    @W22.setter
    def W22(self, value):
        self.uc.reg_write(UC_ARM64_REG_W22, value)


    @property
    def X23(self):
        return self.uc.reg_read(UC_ARM64_REG_X23)

    @X23.setter
    def X23(self, value):
        self.uc.reg_write(UC_ARM64_REG_X23, value)


    @property
    def W23(self):
        return self.uc.reg_read(UC_ARM64_REG_W23)

    @W23.setter
    def W23(self, value):
        self.uc.reg_write(UC_ARM64_REG_W23, value)


    @property
    def X24(self):
        return self.uc.reg_read(UC_ARM64_REG_X24)

    @X24.setter
    def X24(self, value):
        self.uc.reg_write(UC_ARM64_REG_X24, value)


    @property
    def W24(self):
        return self.uc.reg_read(UC_ARM64_REG_W24)

    @W24.setter
    def W24(self, value):
        self.uc.reg_write(UC_ARM64_REG_W24, value)


    @property
    def X25(self):
        return self.uc.reg_read(UC_ARM64_REG_X25)

    @X25.setter
    def X25(self, value):
        self.uc.reg_write(UC_ARM64_REG_X25, value)


    @property
    def W25(self):
        return self.uc.reg_read(UC_ARM64_REG_W25)

    @W25.setter
    def W25(self, value):
        self.uc.reg_write(UC_ARM64_REG_W25, value)


    @property
    def X26(self):
        return self.uc.reg_read(UC_ARM64_REG_X26)

    @X26.setter
    def X26(self, value):
        self.uc.reg_write(UC_ARM64_REG_X26, value)


    @property
    def W26(self):
        return self.uc.reg_read(UC_ARM64_REG_W26)

    @W26.setter
    def W26(self, value):
        self.uc.reg_write(UC_ARM64_REG_W26, value)


    @property
    def X27(self):
        return self.uc.reg_read(UC_ARM64_REG_X27)

    @X27.setter
    def X27(self, value):
        self.uc.reg_write(UC_ARM64_REG_X27, value)


    @property
    def W27(self):
        return self.uc.reg_read(UC_ARM64_REG_W27)

    @W27.setter
    def W27(self, value):
        self.uc.reg_write(UC_ARM64_REG_W27, value)


    @property
    def X28(self):
        return self.uc.reg_read(UC_ARM64_REG_X28)

    @X28.setter
    def X28(self, value):
        self.uc.reg_write(UC_ARM64_REG_X28, value)


    @property
    def W28(self):
        return self.uc.reg_read(UC_ARM64_REG_W28)

    @W28.setter
    def W28(self, value):
        self.uc.reg_write(UC_ARM64_REG_W28, value)


    @property
    def X29(self):
        return self.uc.reg_read(UC_ARM64_REG_X29)

    @X29.setter
    def X29(self, value):
        self.uc.reg_write(UC_ARM64_REG_X29, value)


    @property
    def W29(self):
        return self.uc.reg_read(UC_ARM64_REG_W29)

    @W29.setter
    def W29(self, value):
        self.uc.reg_write(UC_ARM64_REG_W29, value)


    @property
    def X30(self):
        return self.uc.reg_read(UC_ARM64_REG_X30)

    @X30.setter
    def X30(self, value):
        self.uc.reg_write(UC_ARM64_REG_X30, value)


    @property
    def W30(self):
        return self.uc.reg_read(UC_ARM64_REG_W30)

    @W30.setter
    def W30(self, value):
        self.uc.reg_write(UC_ARM64_REG_W30, value)