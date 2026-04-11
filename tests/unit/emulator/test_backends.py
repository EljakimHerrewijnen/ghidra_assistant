import importlib.util
import unittest

from ghidra_assistant.utils.emulator.base_emulator import BaseEmulator


HAS_UNICORN = importlib.util.find_spec("unicorn") is not None
HAS_ANGR = importlib.util.find_spec("angr") is not None
HAS_HEDGEHOG = importlib.util.find_spec("qemu.hedgehog") is not None


class TestEmulatorBackends(unittest.TestCase):
    @unittest.skipUnless(HAS_UNICORN, "unicorn is not installed")
    def test_unicorn_arm64_backend_memory_and_registers(self):
        emu = BaseEmulator(arch="arm64", mode="arm", backend="unicorn")
        base = 0x10000

        emu.mem_map(base, 0x1000, 7)
        emu.mem_write(base, b"\xAA\xBB\xCC\xDD")

        self.assertEqual(emu.mem_read(base, 4), b"\xAA\xBB\xCC\xDD")

        emu.set_register("X0", 0x12345678)
        self.assertEqual(emu.get_register("X0"), 0x12345678)

        emu.set_register("PC", base)
        self.assertEqual(emu.get_register("PC"), base)

    @unittest.skipUnless(HAS_UNICORN, "unicorn is not installed")
    def test_unicorn_arm_thumb_backend_memory_and_registers(self):
        emu = BaseEmulator(arch="arm", mode="thumb", backend="unicorn")
        base = 0x20000

        emu.mem_map(base, 0x1000, 7)
        emu.mem_write(base, b"\x11\x22\x33\x44")

        self.assertEqual(emu.mem_read(base, 4), b"\x11\x22\x33\x44")

        emu.set_register("R0", 0x41414141)
        self.assertEqual(emu.get_register("R0"), 0x41414141)

    @unittest.skipUnless(HAS_ANGR, "angr is not installed")
    def test_angr_backend_memory_and_registers(self):
        emu = BaseEmulator(arch="arm64", mode="arm", backend="angr")
        base = 0x30000

        emu.mem_map(base, 0x2000, 7)
        emu.mem_write(base, b"\xFE\xED\xFA\xCE")

        self.assertEqual(emu.mem_read(base, 4), b"\xFE\xED\xFA\xCE")

        emu.set_register("X0", 0xDEADBEEF)
        self.assertEqual(emu.get_register("X0"), 0xDEADBEEF)

    @unittest.skipUnless(HAS_HEDGEHOG, "qemu.hedgehog is not installed")
    def test_hedgehog_arm64_backend_memory_registers_and_code_hook(self):
        emu = BaseEmulator(arch="arm64", mode="arm", backend="hedgehog")
        try:
            base = 0x40000
            seen = []

            def on_code(_emu, address, size, _user_data):
                seen.append((address, size))
                return len(seen) >= 3

            emu.mem_map(base, 0x1000, 7)
            emu.mem_write(
                base,
                bytes.fromhex("1f2003d5 1f2003d5 1f2003d5".replace(" ", "")),
            )

            self.assertEqual(
                emu.mem_read(base, 12),
                bytes.fromhex("1f2003d5 1f2003d5 1f2003d5".replace(" ", "")),
            )

            emu.set_register("X0", 0x12345678)
            self.assertEqual(emu.get_register("X0"), 0x12345678)

            emu.set_register("PC", base)
            self.assertEqual(emu.get_register("PC"), base)

            emu.hook_code(base, base + 12, on_code)
            emu.emu_start(base, 0)
            self.assertEqual([addr for addr, _size in seen], [base, base + 4, base + 8])
        finally:
            emu.close()

    @unittest.skipUnless(HAS_HEDGEHOG, "qemu.hedgehog is not installed")
    def test_hedgehog_rejects_unsupported_machine_backed_args(self):
        with self.assertRaises(ValueError):
            BaseEmulator(
                arch="arm64",
                mode="arm",
                backend="hedgehog",
                machine_type="raspi3b",
            )

    def test_backend_and_arch_validation(self):
        with self.assertRaises(ValueError):
            BaseEmulator(arch="mips", mode="arm", backend="unicorn")

        with self.assertRaises(ValueError):
            BaseEmulator(arch="arm64", mode="arm", backend="does-not-exist")


if __name__ == "__main__":
    unittest.main()
