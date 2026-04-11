from __future__ import annotations

from typing import Any, Callable, Dict, Iterable

BackendFactory = Callable[[str, str], Any]


class EmulatorHook:
    """Backend-agnostic hook helper."""

    def __init__(self, emulator: "BaseEmulator", addr: int = 0):
        self.emulator = emulator
        self.addr = addr

    def run(self):
        self.hook()

    def hook(self):
        return None

    def hook_unicorn(self, uc, address, size, user_data):
        self.hook()

    def fret(self):
        self.emulator.set_register("PC", self.emulator.get_register("LR"))


class BaseEmulator:
    """Factory-style emulator facade.

    Parameters
    ----------
    arch: str
        Target architecture (for example: ``arm64``, ``aarch64``, ``arm``).
    mode: str
        Execution mode (for example: ``arm`` or ``thumb``).
    backend: str
        Backend identifier (for example: ``unicorn``, ``angr``).
    """

    _BACKEND_FACTORIES: Dict[str, BackendFactory] = {}

    def __init__(self, arch: str, mode: str, backend: str = "unicorn", **backend_kwargs) -> None:
        self.arch = self._normalize_arch(arch)
        self.mode = self._normalize_mode(mode)
        self.backend_name = backend.lower().strip()

        factory = self._BACKEND_FACTORIES.get(self.backend_name)
        if factory is None:
            known = ", ".join(sorted(self._BACKEND_FACTORIES)) or "<none>"
            raise ValueError(f"Unsupported emulator backend '{backend}'. Known backends: {known}")

        self.em = factory(self.arch, self.mode, **backend_kwargs)
        self.mem = getattr(self.em, "mem", None)

    @classmethod
    def register_backend(cls, name: str, factory: BackendFactory) -> None:
        cls._BACKEND_FACTORIES[name.lower().strip()] = factory

    @classmethod
    def available_backends(cls) -> list[str]:
        return sorted(cls._BACKEND_FACTORIES.keys())

    @staticmethod
    def _normalize_arch(arch: str) -> str:
        if not arch:
            raise ValueError("arch is required")
        normalized = arch.lower().strip()
        if normalized in ("arm64", "aarch64", "armv8", "armv8a"):
            return "arm64"
        if normalized in ("arm", "arm32"):
            return "arm"
        if normalized == "riscv32":
            return "riscv32"
        if normalized in ("riscv64", "riscv"):
            return "riscv64"
        if normalized in ("x86", "ia32", "i386", "i686", "x86_32"):
            return "x86"
        if normalized in ("x86_64", "amd64", "x64", "x86-64"):
            return "x86_64"
        raise ValueError(f"Unsupported arch '{arch}'")

    @staticmethod
    def _normalize_mode(mode: str) -> str:
        if not mode:
            raise ValueError("mode is required")
        normalized = mode.lower().strip()
        aliases = {
            "aarch64": "arm",
            "a32": "arm",
            "t32": "thumb",
            "little": "arm",
            "little_endian": "arm",
            "el": "arm",
        }
        return aliases.get(normalized, normalized)

    def __getattr__(self, item):
        return getattr(self.em, item)

    # ------- Common wrappers -------
    def mem_map(self, addr: int, size: int, perms: int):
        return self.em.mem_map(addr, size, perms)

    def mem_unmap(self, addr: int, size: int):
        return self.em.mem_unmap(addr, size)

    def mem_read(self, addr: int, size: int) -> bytes:
        return self.em.mem_read(addr, size)

    def mem_write(self, addr: int, data: bytes):
        return self.em.mem_write(addr, data)

    def mem_regions(self) -> Iterable[tuple[int, int, int]]:
        return self.em.mem_regions()

    def emu_start(self, begin: int, end: int = 0):
        return self.em.emu_start(begin, end)

    def emu_stop(self):
        return self.em.emu_stop()

    def hook_code(self, begin: int, end: int, hook):
        return self.em.hook_code(begin, end, hook)

    def hook_mem_read(self, begin: int, end: int, hook):
        return self.em.hook_mem_read(begin, end, hook)

    def hook_mem_write(self, begin: int, end: int, hook):
        return self.em.hook_mem_write(begin, end, hook)

    def get_register(self, name: str) -> int:
        return self.em.get_register(name)

    def set_register(self, name: str, value: int):
        return self.em.set_register(name, value)

    # ------- Shared helpers -------
    def read_ptr(self, addr: int) -> int:
        return int.from_bytes(self.mem_read(addr, 8), byteorder="little", signed=False)

    def write_ptr(self, addr: int, value: int):
        self.mem_write(addr, int(value).to_bytes(8, byteorder="little", signed=False))

    def read_dword(self, addr: int) -> int:
        return int.from_bytes(self.mem_read(addr, 4), byteorder="little", signed=False)

    def write_dword(self, addr: int, value: int):
        self.mem_write(addr, int(value).to_bytes(4, byteorder="little", signed=False))

    def read_string(self, addr: int, max_length: int = 0x100) -> str:
        out = bytearray()
        for offset in range(max_length):
            byte = self.mem_read(addr + offset, 1)
            if byte == b"\x00":
                break
            out += byte
        return out.decode("utf-8", errors="replace")

    def get_ctx(self) -> dict[str, int]:
        if self.arch == "arm64":
            reg_names = [f"X{i}" for i in range(31)] + ["SP", "PC", "LR", "FP"]
        elif self.arch in ("riscv32", "riscv64"):
            reg_names = [f"X{i}" for i in range(32)] + ["PC"]
        elif self.arch == "x86_64":
            reg_names = [
                "RAX", "RBX", "RCX", "RDX", "RSI", "RDI", "RBP", "RSP",
                "R8", "R9", "R10", "R11", "R12", "R13", "R14", "R15", "RIP",
            ]
        elif self.arch == "x86":
            reg_names = ["EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP", "EIP"]
        else:
            reg_names = [f"R{i}" for i in range(16)] + ["SP", "PC", "LR", "FP"]

        ctx: dict[str, int] = {}
        for reg_name in reg_names:
            try:
                ctx[reg_name] = self.get_register(reg_name)
            except Exception:
                continue
        return ctx


# Register default backends lazily at import time.
def _register_default_backends() -> None:
    from .unicorn_backend import create_unicorn_backend
    from .angr_backend import create_angr_backend
    from .hedgehog_backend import create_hedgehog_backend

    BaseEmulator.register_backend("unicorn", create_unicorn_backend)
    BaseEmulator.register_backend("angr", create_angr_backend)
    BaseEmulator.register_backend("hedgehog", create_hedgehog_backend)


_register_default_backends()
