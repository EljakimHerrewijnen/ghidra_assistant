from ...utils import *
from .misc.sctlr_el3 import SCTLR_EL3 as R_SCTLR_EL3
from .misc.sctlr_el1 import SCTLR_EL1 as R_SCTLR_EL1
from .misc.current_el import CURRENT_EL as R_CURRENT_EL
from .misc.MMU.pagetable_arm64 import PagetableARM64_el3
from .misc.MMU.arm64_mmu import ARM64_MMU
from .misc.tcr_el.tcr_el3 import TCR_EL3 as R_TCR_EL3
from .misc.MMU.mair_eln import MAIR_EL3 as R_MAIR_EL3
from .misc.nzcv import NZCV_Register

if typing.TYPE_CHECKING:
    from utils.debugger.debugger_archs.ga_arm64 import GA_arm64_debugger

X0              = 0
X1              = 1
X2              = 2
X3              = 3
X4              = 4
X5              = 5
X6              = 6
X7              = 7
X8              = 8
X9              = 9
X10             = 10
X11             = 11
X12             = 12
X13             = 13
X14             = 14
X15             = 15
X16             = 16
X17             = 17
X18             = 18
X19             = 19
X20             = 20
X21             = 21
X22             = 22
X23             = 23
X24             = 24
X25             = 25
X26             = 26
X27             = 27
X28             = 28
X29             = 29 # FP
X30             = 30 # LR
SP              = 31 # X31

# Special regs
TTBR0_EL3       = 32
TTBR0_EL2       = 33
TTBR0_EL1       = 34
SCTLR_EL3       = 35
SCTLR_EL2       = 36
SCTLR_EL1       = 37
VBAR_EL3        = 38
VBAR_EL2        = 39
VBAR_EL1        = 40
TCR_EL3         = 41
TCR_EL2         = 42
TCR_EL1         = 43
ELR_EL3         = 44
ELR_EL2         = 45
ELR_EL1         = 46
SP_EL2          = 47
SP_EL1          = 48
SP_EL0          = 49
SPSR_EL3        = 50
SPSR_EL2        = 51
SPSR_EL1        = 52
MAIR_EL3        = 53
MAIR_EL2        = 54
MAIR_EL1        = 55
CURRENT_EL      = 56
NZCV            = 57
DAIF            = 58
TTBR1_EL1       = 59
VTCR_EL2        = 60
VTTBR_EL2       = 61
HCR_EL2         = 62


# Debugger registers
DBG_SETUP_JUMP = 504
DBG_SETUP_JUMP_ADDRESS = 505
DBG_MMU_INTERACT    = 506
DBG_JUMP_TO         = 507
DBG_CONT_EXEC       = 508
TEMP_STORAGE        = 509
EXCEPTION_ID        = 510
JUMP_ADDR           = 511

class ARM64_Concrete_State:
    '''
        Class that will interact with the concrete device for getting and writing the processor state.
    '''
    def __init__(self, base_config_address : int, debugger : "GA_arm64_debugger", auto_sync=False, auto_sync_special=False) -> None:
        self.baddr = base_config_address
        self.debugger = debugger
        self.auto_sync = auto_sync
        self.auto_sync_special = auto_sync_special
        self.mmu = ARM64_MMU(self)

    def loadQ(self, addr):
        return struct.unpack("<Q", self.debugger.memdump_region(addr, 8))[0]

    def config_addr(self, config):
        return self.baddr + config * 8

    def write_config(self, config, value : int, do_not_sync=False):
        self.debugger.memwrite_region(self.config_addr(config), struct.pack("<Q", value))
        if do_not_sync:
            return
        if self.auto_sync:
            self.debugger.sync_state()
        if self.auto_sync_special:
            self.debugger.sync_special_regs()

    def restore_ctx(self, ctx : dict[str, int]):
        for reg, value in ctx.items():
            if reg.startswith("X"):
                self.__setattr__(reg, value)
        if self.auto_sync:
            self.debugger.sync_state()

    def get_ctx(self, as_dict=False):
        '''
        TODO write as dict with registers and values
        '''
        if as_dict:
            ret = {}
            for i in range(31):
                ret[f"X{i}"] = getattr(self, f"X{i}")
            return ret
        state  = f"""
             PC: 0x????????????????\t LR: 0x{self.LR:16x}\t SP: 0x{self.SP:16x}\t FP: 0x{self.FP:16x}
             X0: 0x{self.X0:16x}\t X1: 0x{self.X1:16x}\t X2: 0x{self.X2:16x}\t X3: 0x{self.X3:16x}\t
             X4: 0x{self.X4:16x}\t X5: 0x{self.X5:16x}\t X6: 0x{self.X6:16x}\t X7: 0x{self.X7:16x}\t
             X8: 0x{self.X8:16x}\t X9: 0x{self.X9:16x}\tX10: 0x{self.X10:16x}\tX11: 0x{self.X11:16x}\t
            X12: 0x{self.X12:16x}\tX13: 0x{self.X13:16x}\tX14: 0x{self.X14:16x}\tX15: 0x{self.X15:16x}\t
            X16: 0x{self.X16:16x}\tX17: 0x{self.X17:16x}\tX18: 0x{self.X18:16x}\tX19: 0x{self.X19:16x}\t
            X20: 0x{self.X20:16x}\tX21: 0x{self.X21:16x}\tX22: 0x{self.X22:16x}\tX23: 0x{self.X23:16x}\t
            X24: 0x{self.X24:16x}\tX25: 0x{self.X25:16x}\tX26: 0x{self.X26:16x}\tX27: {self.X27:#18x}\t
            X28: 0x{self.X28:16x}\tX29: 0x{self.X29:16x}\tX30: 0x{self.X30:16x}
        """
        return state

    def get_special(self):
        special_state = f"""
            VBAR_EL3: 0x{self.VBAR_EL3:16x}\tVBAR_EL2: 0x{self.VBAR_EL2:16x}\tVBAR_EL1: 0x{self.VBAR_EL1:16x}
            TTBR0_EL3: 0x{self.TTBR0_EL3:16x}\tTTBR0_EL2: 0x{self.TTBR0_EL2:16x}\tTTBR0_EL1: 0x{self.TTBR0_EL1:16x}
            SCTLR_EL3: 0x{self.SCTLR_EL3:16x}\tSCTLR_EL2: 0x{self.SCTLR_EL2:16x}\tSCTLR_EL1: 0x{self.SCTLR_EL1:16x}
            TCR_EL3: 0x{self.TCR_EL3:16x}\tTCR_EL2: 0x{self.TCR_EL2:16x}\tTCR_EL1: 0x{self.TCR_EL1:16x}
            VTCR_EL2: 0x{self.VTCR_EL2:16x}\tVTTBR_EL2: 0x{self.VTTBR_EL2:16x}
            ELR_EL3: 0x{self.ELR_EL3:16x}\tELR_EL2: 0x{self.ELR_EL2:16x}\tELR_EL1: 0x{self.ELR_EL1:16x}
            current_el: 0x{self.R_CURRENT_EL.get_exception_level()}
        """
        return special_state

    def print_ctx(self):
        p_info(self.get_ctx())

    def read_config(self, config):
        return struct.unpack("<Q", self.debugger.memdump_region(self.config_addr(config), 8))[0]

    def mem_read(self, address, length) -> bytes:
        return self.debugger.memdump_region(address, length)

    def mem_write(self, address, data):
        self.debugger.memwrite_region(address, data)

    @property
    def DEBUGGER_JUMP(self):
        return self.read_config(JUMP_ADDR)

    @DEBUGGER_JUMP.setter
    def DEBUGGER_JUMP(self, value : bytes):
        self.write_config(JUMP_ADDR, value, True)

    @property
    def EXCEPTION_ID(self):
        return self.read_config(EXCEPTION_ID)

    @EXCEPTION_ID.setter
    def EXCEPTION_ID(self, value : bytes):
        self.write_config(EXCEPTION_ID, value, True)

    @property
    def DBG_CONT_EXEC(self):
        return self.read_config(DBG_CONT_EXEC)

    @DBG_CONT_EXEC.setter
    def DBG_CONT_EXEC(self, value : int):
        self.write_config(DBG_CONT_EXEC, value, True)

    @property
    def DBG_JUMP_TO(self):
        return self.read_config(DBG_JUMP_TO)

    @DBG_JUMP_TO.setter
    def DBG_JUMP_TO(self, value : int):
        self.write_config(DBG_JUMP_TO, value, True)

    @property
    def DBG_MMU_INTERACT(self):
        return self.read_config(DBG_MMU_INTERACT)

    @DBG_MMU_INTERACT.setter
    def DBG_MMU_INTERACT(self, value : int):
        self.write_config(DBG_MMU_INTERACT, value, True)

    @property
    def DBG_SETUP_JUMP(self):
        return self.read_config(DBG_SETUP_JUMP)

    @DBG_SETUP_JUMP.setter
    def DBG_SETUP_JUMP(self, value : int):
        self.write_config(DBG_SETUP_JUMP, value, True)

    @property
    def DBG_SETUP_JUMP_ADDRESS(self):
        return self.read_config(DBG_SETUP_JUMP_ADDRESS)

    @DBG_SETUP_JUMP_ADDRESS.setter
    def DBG_SETUP_JUMP_ADDRESS(self, value : int):
        self.write_config(DBG_SETUP_JUMP_ADDRESS, value, True)

    # ================ VBAR ================
    @property
    def VBAR_EL3(self):
        return self.read_config(VBAR_EL3)

    @VBAR_EL3.setter
    def VBAR_EL3(self, value : bytes):
        self.write_config(VBAR_EL3, value)

    @property
    def VBAR_EL2(self):
        return self.read_config(VBAR_EL2)

    @VBAR_EL2.setter
    def VBAR_EL2(self, value : bytes):
        self.write_config(VBAR_EL2, value)

    @property
    def VBAR_EL1(self):
        return self.read_config(VBAR_EL1)

    @VBAR_EL1.setter
    def VBAR_EL1(self, value : bytes):
        self.write_config(VBAR_EL1, value)
    # ================ VBAR ================

    # ================ TTBR0_EL ================
    @property
    def TTBR0_EL3(self):
        return self.read_config(TTBR0_EL3)

    @TTBR0_EL3.setter
    def TTBR0_EL3(self, value : bytes):
        self.write_config(TTBR0_EL3, value)

    @property
    def TTBR0_EL2(self):
        return self.read_config(TTBR0_EL2)

    @TTBR0_EL2.setter
    def TTBR0_EL2(self, value : bytes):
        self.write_config(TTBR0_EL2, value)

    @property
    def TTBR0_EL1(self):
        return self.read_config(TTBR0_EL1)

    @TTBR0_EL1.setter
    def TTBR0_EL1(self, value : bytes):
        self.write_config(TTBR0_EL1, value)

    @property
    def TTBR1_EL1(self):
        return self.read_config(TTBR1_EL1)

    @TTBR1_EL1.setter
    def TTBR1_EL1(self, value : bytes):
        self.write_config(TTBR1_EL1, value)
    # ================ TTBR0_EL ================

    # ================ SCTLR_EL ================
    @property
    def SCTLR_EL3(self):
        return self.read_config(SCTLR_EL3)

    @SCTLR_EL3.setter
    def SCTLR_EL3(self, value : bytes):
        self.write_config(SCTLR_EL3, value)

    @property
    def R_SCTLR_EL3(self):
        return R_SCTLR_EL3(self.SCTLR_EL3)

    @R_SCTLR_EL3.setter
    def R_SCTLR_EL3(self, value : int):
        #TODO make bits in control register r/w
        self.SCTLR_EL3 = struct.pack("<Q", value)

    @property
    def SCTLR_EL2(self):
        return self.read_config(SCTLR_EL2)

    @SCTLR_EL2.setter
    def SCTLR_EL2(self, value : bytes):
        self.write_config(SCTLR_EL2, value)

    @property
    def SCTLR_EL1(self):
        return self.read_config(SCTLR_EL1)

    @SCTLR_EL1.setter
    def SCTLR_EL1(self, value : bytes):
        self.write_config(SCTLR_EL1, value)

    @property
    def R_SCTLR_EL1(self):
        return R_SCTLR_EL1(self.SCTLR_EL1)

    @R_SCTLR_EL1.setter
    def R_SCTLR_EL1(self, value : int):
        #TODO make bits in control register r/w
        self.SCTLR_EL1 = struct.pack("<Q", value)
    # ================ SCTLR_EL ================


    @property
    def R_CURRENT_EL(self):
        return R_CURRENT_EL(self.CURRENT_EL)

    @R_CURRENT_EL.setter
    def R_CURRENT_EL(self, value : int):
        # TODO write bits to set current EL
        return NotImplemented

    # ================ TCR_EL ================
    @property
    def TCR_EL3(self):
        return self.read_config(TCR_EL3)

    @TCR_EL3.setter
    def TCR_EL3(self, value : bytes):
        self.write_config(TCR_EL3, value)

    @property
    def R_TCR_EL3(self):
        return R_TCR_EL3(self.TCR_EL3)

    @R_TCR_EL3.setter
    def R_TCR_EL3(self, value : int):
        self.TCR_EL3 = struct.pack("<Q", value)

    @property
    def TCR_EL2(self):
        return self.read_config(TCR_EL2)

    @TCR_EL2.setter
    def TCR_EL2(self, value : bytes):
        self.write_config(TCR_EL2, value)

    @property
    def TCR_EL1(self):
        return self.read_config(TCR_EL1)

    @TCR_EL1.setter
    def TCR_EL1(self, value : bytes):
        self.write_config(TCR_EL1, value)

    @property
    def VTCR_EL2(self):
        return self.read_config(VTCR_EL2)

    @VTCR_EL2.setter
    def VTCR_EL2(self, value : bytes):
        self.write_config(VTCR_EL2, value)

    # TODO make this a class

    @property
    def VTTBR_EL2(self):
        return self.read_config(VTTBR_EL2)

    @VTTBR_EL2.setter
    def VTTBR_EL2(self, value : bytes):
        self.write_config(VTTBR_EL2, value)

    @property
    def HCR_EL2(self):
        return self.read_config(HCR_EL2)

    @HCR_EL2.setter
    def HCR_EL2(self, value : bytes):
        self.write_config(HCR_EL2, value)

    # ================ TCR_EL ================

    # ================ ELR_EL ================
    @property
    def ELR_EL3(self):
        return self.read_config(ELR_EL3)

    @ELR_EL3.setter
    def ELR_EL3(self, value : bytes):
        self.write_config(ELR_EL3, value)

    @property
    def ELR_EL2(self):
        return self.read_config(ELR_EL2)

    @ELR_EL2.setter
    def ELR_EL2(self, value : bytes):
        self.write_config(ELR_EL2, value)

    @property
    def ELR_EL1(self):
        return self.read_config(ELR_EL1)

    @ELR_EL1.setter
    def ELR_EL1(self, value : bytes):
        self.write_config(ELR_EL1, value)

    # ================ ELR_EL ================

    # ================ SP_EL ================
    @property
    def SP_EL2(self):
        return self.read_config(SP_EL2)

    @SP_EL2.setter
    def SP_EL2(self, value : bytes):
        self.write_config(SP_EL2, value)

    @property
    def SP_EL1(self):
        return self.read_config(SP_EL1)

    @SP_EL1.setter
    def SP_EL1(self, value : bytes):
        self.write_config(SP_EL1, value)

    @property
    def SP_EL0(self):
        return self.read_config(SP_EL0)

    @SP_EL0.setter
    def SP_EL0(self, value : bytes):
        self.write_config(SP_EL0, value)

    # ================ SP_EL ================

    # ================ SPSR_EL ================
    @property
    def SPSR_EL3(self):
        return self.read_config(SPSR_EL3)

    @SPSR_EL3.setter
    def SPSR_EL3(self, value : bytes):
        self.write_config(SPSR_EL3, value)

    @property
    def SPSR_EL2(self):
        return self.read_config(SPSR_EL2)

    @SPSR_EL2.setter
    def SPSR_EL2(self, value : bytes):
        self.write_config(SPSR_EL2, value)

    @property
    def SPSR_EL1(self):
        return self.read_config(SPSR_EL1)

    @SPSR_EL1.setter
    def SPSR_EL1(self, value : bytes):
        self.write_config(SPSR_EL1, value)

    # ================ SPSR_EL ================

    # ================ MAIR_EL ================

    @property
    def MAIR_EL3(self):
        return self.read_config(MAIR_EL3)

    @MAIR_EL3.setter
    def MAIR_EL3(self, value : bytes):
        self.write_config(MAIR_EL3, value)

    @property
    def R_MAIR_EL3(self):
        return R_MAIR_EL3(self.MAIR_EL3)

    @R_MAIR_EL3.setter
    def R_MAIR_EL3(self, value : int):
        self.MAIR_EL3 = struct.pack("<Q", value)

    @property
    def MAIR_EL2(self):
        return self.read_config(MAIR_EL2)

    @MAIR_EL2.setter
    def MAIR_EL2(self, value : bytes):
        self.write_config(MAIR_EL2, value)

    @property
    def MAIR_EL1(self):
        return self.read_config(MAIR_EL1)

    @MAIR_EL1.setter
    def MAIR_EL1(self, value : bytes):
        self.write_config(MAIR_EL1, value)

    # ================ MAIR_EL ================

    @property
    def CURRENT_EL(self):
        return self.read_config(CURRENT_EL)

    @CURRENT_EL.setter
    def CURRENT_EL(self, value : bytes):
        warn("CurrentEL does nothing, not synced in debugger")
        self.write_config(CURRENT_EL, value)

    # ================ NZCV ================
    @property
    def NZCV(self):
        return self.read_config(NZCV)

    @NZCV.setter
    def NZCV(self, value : bytes):
        self.write_config(NZCV, value)

    @property
    def R_NZCV(self):
        return NZCV_Register(self.NZCV)

    @R_NZCV.setter
    def R_NZCV(self, value : int):
        self.NZCV = struct.pack("<Q", value)

    # ================ NZCV ================

    # ================ DAIF ================
    @property
    def DAIF(self):
        return self.read_config(DAIF)

    @DAIF.setter
    def DAIF(self, value : bytes):
        self.write_config(DAIF, value)

    # TODO make this a class
    # ================ DAIF ================

    @property
    def LR(self):
        return self.read_config(X30)

    @LR.setter
    def LR(self, value : bytes):
        self.write_config(X30, value)

    # SP also register X31
    @property
    def SP(self):
        return self.read_config(SP)

    @SP.setter
    def SP(self, value : bytes):
        self.write_config(SP, value)

    @property
    def FP(self):
        return self.read_config(X29)

    @FP.setter
    def FP(self, value : bytes):
        self.write_config(X29, value)

    def print_ctx(self):
        info(
            f"""
            X0 : {hex(self.X0)} | X1 : {hex(self.X1)} | X2 : {hex(self.X2)} | X3 : {hex(self.X3)} | X4 : {hex(self.X4)} | X5 : {hex(self.X5)} | X6 : {hex(self.X6)} |
            X7 : {hex(self.X7)} | X8 : {hex(self.X8)} | X9 : {hex(self.X9)} | X10 : {hex(self.X10)} | X11 : {hex(self.X11)} | X12 : {hex(self.X12)} | X13 : {hex(self.X13)} |
            X14 : {hex(self.X14)} | X15 : {hex(self.X15)} | X16 : {hex(self.X16)} | X17 : {hex(self.X17)} | X18 : {hex(self.X18)} | X19 : {hex(self.X19)} | X20 : {hex(self.X20)} |
            X21 : {hex(self.X21)} | X22 : {hex(self.X22)} | X23 : {hex(self.X23)} | X24 : {hex(self.X24)} | X25 : {hex(self.X25)} | X26 : {hex(self.X26)} | X27 : {hex(self.X27)} |
            X28 : {hex(self.X28)} | X29 : {hex(self.X29)} | LR/X30 : {hex(self.X30)} | SP/X31 : {hex(self.SP)}
        """)

    @property
    def arm64_el3_1lvl_ptp(self):
        '''
        Perform a pagewalk for EL3 level 1 pagetable
        '''
        addr = struct.unpack("<Q", self.debugger.memdump_region(self.TTBR0_EL3, 8))[0]
        base_addr = addr - (addr % 0x1000)
        ptp_len = (addr % 0x1000) #!!Unknown if this is the actual length of the pagetables.
        ptp_dump = self.debugger.memdump_region(base_addr, ptp_len * 0x1000)
        return PagetableARM64_el3(ptp_dump)

    # Auto generated
    @property
    def X0(self):
        return self.read_config(X0)

    @X0.setter
    def X0(self, value : int):
        self.write_config(X0, value)

    @property
    def X1(self):
        return self.read_config(X1)

    @X1.setter
    def X1(self, value : int):
        self.write_config(X1, value)

    @property
    def X2(self):
        return self.read_config(X2)

    @X2.setter
    def X2(self, value : int):
        self.write_config(X2, value)

    @property
    def X3(self):
        return self.read_config(X3)

    @X3.setter
    def X3(self, value : int):
        self.write_config(X3, value)

    @property
    def X4(self):
        return self.read_config(X4)

    @X4.setter
    def X4(self, value : int):
        self.write_config(X4, value)

    @property
    def X5(self):
        return self.read_config(X5)

    @X5.setter
    def X5(self, value : int):
        self.write_config(X5, value)

    @property
    def X6(self):
        return self.read_config(X6)

    @X6.setter
    def X6(self, value : int):
        self.write_config(X6, value)

    @property
    def X7(self):
        return self.read_config(X7)

    @X7.setter
    def X7(self, value : int):
        self.write_config(X7, value)

    @property
    def X8(self):
        return self.read_config(X8)

    @X8.setter
    def X8(self, value : int):
        self.write_config(X8, value)

    @property
    def X9(self):
        return self.read_config(X9)

    @X9.setter
    def X9(self, value : int):
        self.write_config(X9, value)

    @property
    def X10(self):
        return self.read_config(X10)

    @X10.setter
    def X10(self, value : int):
        self.write_config(X10, value)

    @property
    def X11(self):
        return self.read_config(X11)

    @X11.setter
    def X11(self, value : int):
        self.write_config(X11, value)

    @property
    def X12(self):
        return self.read_config(X12)

    @X12.setter
    def X12(self, value : int):
        self.write_config(X12, value)

    @property
    def X13(self):
        return self.read_config(X13)

    @X13.setter
    def X13(self, value : int):
        self.write_config(X13, value)

    @property
    def X14(self):
        return self.read_config(X14)

    @X14.setter
    def X14(self, value : int):
        self.write_config(X14, value)

    @property
    def X15(self):
        return self.read_config(X15)

    @X15.setter
    def X15(self, value : int):
        self.write_config(X15, value)

    @property
    def X16(self):
        return self.read_config(X16)

    @X16.setter
    def X16(self, value : int):
        self.write_config(X16, value)

    @property
    def X17(self):
        return self.read_config(X17)

    @X17.setter
    def X17(self, value : int):
        self.write_config(X17, value)

    @property
    def X18(self):
        return self.read_config(X18)

    @X18.setter
    def X18(self, value : int):
        self.write_config(X18, value)

    @property
    def X19(self):
        return self.read_config(X19)

    @X19.setter
    def X19(self, value : int):
        self.write_config(X19, value)

    @property
    def X20(self):
        return self.read_config(X20)

    @X20.setter
    def X20(self, value : int):
        self.write_config(X20, value)

    @property
    def X21(self):
        return self.read_config(X21)

    @X21.setter
    def X21(self, value : int):
        self.write_config(X21, value)

    @property
    def X22(self):
        return self.read_config(X22)

    @X22.setter
    def X22(self, value : int):
        self.write_config(X22, value)

    @property
    def X23(self):
        return self.read_config(X23)

    @X23.setter
    def X23(self, value : int):
        self.write_config(X23, value)

    @property
    def X24(self):
        return self.read_config(X24)

    @X24.setter
    def X24(self, value : int):
        self.write_config(X24, value)

    @property
    def X25(self):
        return self.read_config(X25)

    @X25.setter
    def X25(self, value : int):
        self.write_config(X25, value)

    @property
    def X26(self):
        return self.read_config(X26)

    @X26.setter
    def X26(self, value : int):
        self.write_config(X26, value)

    @property
    def X27(self):
        return self.read_config(X27)

    @X27.setter
    def X27(self, value : int):
        self.write_config(X27, value)

    @property
    def X28(self):
        return self.read_config(X28)

    @X28.setter
    def X28(self, value : int):
        self.write_config(X28, value)

    @property
    def X29(self):
        return self.read_config(X29)

    @X29.setter
    def X29(self, value : int):
        self.write_config(X29, value)

    @property
    def X30(self):
        return self.read_config(X30)

    @X30.setter
    def X30(self, value : int):
        self.write_config(X30, value)

    @property
    def X31(self):
        return self.SP

    @X31.setter
    def X31(self, value : int):
        self.SP = value

    # All W0 - W30 are aliases to X0 - X30
    @property
    def W0(self):
        return self.X0 & 0xFFFFFFFF

    @W0.setter
    def W0(self, value : int):
        self.X0 = (self.X0 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W1(self):
        return self.X1 & 0xFFFFFFFF

    @W1.setter
    def W1(self, value : int):
        self.X1 = (self.X1 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W2(self):
        return self.X2 & 0xFFFFFFFF

    @W2.setter
    def W2(self, value : int):
        self.X2 = (self.X2 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W3(self):
        return self.X3 & 0xFFFFFFFF

    @W3.setter
    def W3(self, value : int):
        self.X3 = (self.X3 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W4(self):
        return self.X4 & 0xFFFFFFFF

    @W4.setter
    def W4(self, value : int):
        self.X4 = (self.X4 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W5(self):
        return self.X5 & 0xFFFFFFFF

    @W5.setter
    def W5(self, value : int):
        self.X5 = (self.X5 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W6(self):
        return self.X6 & 0xFFFFFFFF

    @W6.setter
    def W6(self, value : int):
        self.X6 = (self.X6 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W7(self):
        return self.X7 & 0xFFFFFFFF

    @W7.setter
    def W7(self, value : int):
        self.X7 = (self.X7 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W8(self):
        return self.X8 & 0xFFFFFFFF

    @W8.setter
    def W8(self, value : int):
        self.X8 = (self.X8 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W9(self):
        return self.X9 & 0xFFFFFFFF

    @W9.setter
    def W9(self, value : int):
        self.X9 = (self.X9 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W10(self):
        return self.X10 & 0xFFFFFFFF

    @W10.setter
    def W10(self, value : int):
        self.X10 = (self.X10 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W11(self):
        return self.X11 & 0xFFFFFFFF

    @W11.setter
    def W11(self, value : int):
        self.X11 = (self.X11 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W12(self):
        return self.X12 & 0xFFFFFFFF

    @W12.setter
    def W12(self, value : int):
        self.X12 = (self.X12 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W13(self):
        return self.X13 & 0xFFFFFFFF

    @W13.setter
    def W13(self, value : int):
        self.X13 = (self.X13 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W14(self):
        return self.X14 & 0xFFFFFFFF

    @W14.setter
    def W14(self, value : int):
        self.X14 = (self.X14 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W15(self):
        return self.X15 & 0xFFFFFFFF

    @W15.setter
    def W15(self, value : int):
        self.X15 = (self.X15 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W16(self):
        return self.X16 & 0xFFFFFFFF

    @W16.setter
    def W16(self, value : int):
        self.X16 = (self.X16 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W17(self):
        return self.X17 & 0xFFFFFFFF

    @W17.setter
    def W17(self, value : int):
        self.X17 = (self.X17 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W18(self):
        return self.X18 & 0xFFFFFFFF

    @W18.setter
    def W18(self, value : int):
        self.X18 = (self.X18 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W19(self):
        return self.X19 & 0xFFFFFFFF

    @W19.setter
    def W19(self, value : int):
        self.X19 = (self.X19 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W20(self):
        return self.X20 & 0xFFFFFFFF

    @W20.setter
    def W20(self, value : int):
        self.X20 = (self.X20 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W21(self):
        return self.X21 & 0xFFFFFFFF

    @W21.setter
    def W21(self, value : int):
        self.X21 = (self.X21 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W22(self):
        return self.X22 & 0xFFFFFFFF

    @W22.setter
    def W22(self, value : int):
        self.X22 = (self.X22 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W23(self):
        return self.X23 & 0xFFFFFFFF

    @W23.setter
    def W23(self, value : int):
        self.X23 = (self.X23 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W24(self):
        return self.X24 & 0xFFFFFFFF

    @W24.setter
    def W24(self, value : int):
        self.X24 = (self.X24 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W25(self):
        return self.X25 & 0xFFFFFFFF

    @W25.setter
    def W25(self, value : int):
        self.X25 = (self.X25 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W26(self):
        return self.X26 & 0xFFFFFFFF

    @W26.setter
    def W26(self, value : int):
        self.X26 = (self.X26 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W27(self):
        return self.X27 & 0xFFFFFFFF

    @W27.setter
    def W27(self, value : int):
        self.X27 = (self.X27 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W28(self):
        return self.X28 & 0xFFFFFFFF

    @W28.setter
    def W28(self, value : int):
        self.X28 = (self.X28 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W29(self):
        return self.X29 & 0xFFFFFFFF

    @W29.setter
    def W29(self, value : int):
        self.X29 = (self.X29 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

    @property
    def W30(self):
        return self.X30 & 0xFFFFFFFF

    @W30.setter
    def W30(self, value : int):
        self.X30 = (self.X30 & 0xFFFFFFFF00000000) | (value & 0xFFFFFFFF)

