from ..riscv_stepper import RiscvStepper


class Riscv32Stepper(RiscvStepper):
    def __init__(self, emulator, state=None, debug_log: bool = False) -> None:
        if int(getattr(emulator, "_bits", 32)) != 32:
            raise ValueError("Riscv32Stepper requires a 32-bit RISC-V emulator")
        super().__init__(emulator, state=state, debug_log=debug_log)


__all__ = ["Riscv32Stepper"]
