from ...utils import *

if typing.TYPE_CHECKING:
    from utils.debugger.debugger_archs.ga_arm_thumb import GA_arm_thumb_debugger

# https://developer.arm.com/documentation/ddi0210/c/Programmer-s-Model/Registers/The-Thumb-state-register-set
'''
R8: Register used as the Indirect Function Call Target (IFC).
R9: Register used as the Platform Register (P).
R10: Register used as the Thread Pointer (TP) or Global Pointer (GP).
R11: Register used as the Frame Pointer (FP) in some calling conventions.
R12: Register used as the Intra-Procedure-call-scratched-Register (IP), also known as the scratch register.
R13: Register used as the Stack Pointer (SP), which points to the top of the stack.
R14: Register used as the Link Register (LR), which holds the return address when a function call is made.
R15: Register used as the Program Counter (PC), which holds the address of the current instruction being executed.
'''
R0              = 0
R1              = 1
R2              = 2
R3              = 3
R4              = 4
R5              = 5
R6              = 6
R7              = 7
R8              = 7
R9              = 9
R10             = 10
R11             = 11
R12             = 12
R13             = 13
R14             = 14
R15             = 15

# Special purpose (R8-R15)
IFC             = 8
P               = 9 
GP              = 10
FP              = 11
IP              = 12
SP              = 13 
LR              = 14 
PC              = 15 

# Special regs TODO


# Debugger registers
DBG_MMU_INTERACT    = 506
DBG_JUMP_TO         = 507
DBG_CONT_EXEC       = 508
TEMP_STORAGE        = 509
EXCEPTION_ID        = 510
JUMP_ADDR           = 511
# Below is still 2048 bytes of memory to be used.

class ARMThumb_Concrete_State:
    '''
        Class that will interact with the concrete device for getting and writing the processor state.

        For Thumb documentation
        https://developer.arm.com/documentation/ddi0210/c/CACBCAAE
    '''
    def __init__(self, base_config_address : int, debugger : "GA_arm_thumb_debugger", auto_sync=True, auto_sync_special=True) -> None:
        self.baddr = base_config_address
        self.debugger = debugger
        self.auto_sync = auto_sync
        self.auto_sync_special = auto_sync_special
        # TODO add MMU

    def config_addr(self, config):
        return self.baddr + config * 4

    def write_config(self, config, value : int, do_not_sync=False):
        self.debugger.memwrite_region(self.config_addr(config), struct.pack("<Q", value))
        if do_not_sync:
            return
        if self.auto_sync:
            self.debugger.sync_state()
        if self.auto_sync_special:
            self.debugger.sync_special_regs()

    def read_config(self, config):
        return struct.unpack("<I", self.debugger.memdump_region(self.config_addr(config), 4))[0]
    
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
    
    # Special purpose registers
    @property
    def IFC(self): #R8
        return self.read_config(IFC)
    
    @IFC.setter
    def IFC(self, value : bytes):
        self.write_config(IFC, value)

    @property
    def P(self): # R9
        return self.read_config(P)
    
    @P.setter
    def P(self, value : bytes):
        self.write_config(P, value)

    @property
    def GP(self): #R10
        return self.read_config(GP)
    
    @GP.setter
    def GP(self, value : bytes):
        self.write_config(GP, value)

    @property
    def FP(self): #R11
        return self.read_config(FP)
    
    @FP.setter
    def FP(self, value : bytes):
        self.write_config(FP, value)

    @property
    def IP(self): #R12
        return self.read_config(IP)
    
    @IP.setter
    def IP(self, value : bytes):
        self.write_config(IP, value)
    
    @property
    def LR(self): # #R14
        return self.read_config(LR)
    
    @LR.setter
    def LR(self, value : bytes):
        self.write_config(LR, value)
    
    @property
    def SP(self): #R13
        return self.read_config(SP)
    
    @SP.setter
    def SP(self, value : bytes):
        self.write_config(SP, value)

    @property
    def PC(self): #R15
        return self.read_config(PC)
    
    @PC.setter
    def PC(self, value : bytes):
        self.write_config(PC, value)

    # Auto generated
    @property
    def R0(self):
        return self.read_config(R0)
    
    @R0.setter
    def R0(self, value : int):
        self.write_config(R0, value)
    

    @property
    def R1(self):
        return self.read_config(R1)
    
    @R1.setter
    def R1(self, value : int):
        self.write_config(R1, value)
    

    @property
    def R2(self):
        return self.read_config(R2)
    
    @R2.setter
    def R2(self, value : int):
        self.write_config(R2, value)
    

    @property
    def R3(self):
        return self.read_config(R3)
    
    @R3.setter
    def R3(self, value : int):
        self.write_config(R3, value)
    

    @property
    def R4(self):
        return self.read_config(R4)
    
    @R4.setter
    def R4(self, value : int):
        self.write_config(R4, value)
    

    @property
    def R5(self):
        return self.read_config(R5)
    
    @R5.setter
    def R5(self, value : int):
        self.write_config(R5, value)
    

    @property
    def R6(self):
        return self.read_config(R6)
    
    @R6.setter
    def R6(self, value : int):
        self.write_config(R6, value)
    

    @property
    def R7(self):
        return self.read_config(R7)
    
    @R7.setter
    def R7(self, value : int):
        self.write_config(R7, value)
    

    @property
    def R8(self):
        return self.read_config(R8)
    
    @R8.setter
    def R8(self, value : int):
        self.write_config(R8, value)
    

    @property
    def R9(self):
        return self.read_config(R9)
    
    @R9.setter
    def R9(self, value : int):
        self.write_config(R9, value)
    

    @property
    def R10(self):
        return self.read_config(R10)
    
    @R10.setter
    def R10(self, value : int):
        self.write_config(R10, value)
    

    @property
    def R11(self):
        return self.read_config(R11)
    
    @R11.setter
    def R11(self, value : int):
        self.write_config(R11, value)
    

    @property
    def R12(self):
        return self.read_config(R12)
    
    @R12.setter
    def R12(self, value : int):
        self.write_config(R12, value)
    

    @property
    def R13(self):
        return self.read_config(R13)
    
    @R13.setter
    def R13(self, value : int):
        self.write_config(R13, value)
    

    @property
    def R14(self):
        return self.read_config(R14)
    
    @R14.setter
    def R14(self, value : int):
        self.write_config(R14, value)
    

    @property
    def R15(self):
        return self.read_config(R15)
    
    @R15.setter
    def R15(self, value : int):
        self.write_config(R15, value)