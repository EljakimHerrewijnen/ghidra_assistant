from ..riscv_stepper import RiscvStepper


class Riscv64Stepper(RiscvStepper):
    def __init__(self, emulator, state=None, debug_log: bool = False) -> None:
        if int(getattr(emulator, "_bits", 64)) != 64:
            raise ValueError("Riscv64Stepper requires a 64-bit RISC-V emulator")
        super().__init__(emulator, state=state, debug_log=debug_log)


__all__ = ["Riscv64Stepper"]
