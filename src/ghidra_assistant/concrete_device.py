from .ghidra_assistant import *
import argparse
import importlib
from .utils.utils import *
from .utils.debugger.debugger_archs.base_arch import BaseArch_debugger

class Mem:
    def __init__(self, cd : "ConcreteDevice"):
        self.cd = cd

    def __getitem__(self, key):
        # Check if 'key' is a slice object
        if isinstance(key, slice):
            # Extract the start, stop, and step attributes of the slice
            start = key.start
            size = key.stop - start

            return self.cd.memdump_region(start, size)
        else:
            # Handle single item access if needed
            return self.cd.memdump_region(key, 1)

    def __setitem__(self, key, value):
        # Check if 'key' is a slice object
        if isinstance(key, slice):
            # Extract the start, stop, and step attributes of the slice
            start = key.start
            size = key.stop - start

            return self.cd.memwrite_region(start, value)
        else:
            # Handle single item access if needed
            return self.cd.memwrite_region(key, value)

class ConcreteDevice():
    '''
        Object that handles the communication between a 'real' target device and the GA
    '''
    def __init__(self, target_dev : str = None, connectga=False):
        if connectga:
            self.connect_GA()
        # SET THESE! TODO ADD CHECKS
        self.arch = "ARM"
        self.ga_debugger_location = 0x100000
        self.ga_vbar_location = 0x101000
        self.ga_storage_location = 0x102000
        self.ga_stack_location = 0x103000
        self.transmission_size = 0x200 # Default, change if needed.
        self.mem = Mem(self)

        # Is different than ga_debugger_location because it is a direct reference to the debugger_main function
        self.debugger_main = self.ga_debugger_location

        self.arch_dbg = BaseArch_debugger(self.ga_vbar_location, self.ga_debugger_location, self.ga_storage_location)
        self.target_dev = target_dev
        self.connectga = connectga
        self.dev = None
        self.concrete_memory_ranges = []
        if target_dev is not None:
            self.insert_hooks_from_file(target_dev)

    def relocate_debugger(self, vbar_location, debugger_location, storage_location):

        def range_intersect(x: range, y: range) -> bool:
            assert x.step == y.step == 1
            return not (y.stop < x.start or x.stop < y.start)

        # Do range checks - vbar, debugger and storage need to be at least 0x1000 apart
        vbar_region = range(vbar_location, vbar_location + 0x1000)
        debugger_region = range(debugger_location, debugger_location + 0x1000)
        storage_region = range(storage_location, storage_location + 0x1000)

        if range_intersect(vbar_region, debugger_region) or range_intersect(debugger_region, storage_region) or range_intersect(storage_region, vbar_region):
            raise ValueError("vbar, debugger and storage must be at least 0x1000 apart.")

        self.arch_dbg.storage_addr = storage_location
        self.arch_dbg.vector_table_addr = vbar_location
        self.arch_dbg.debugger_addr = debugger_location

        self.ga_debugger_location = debugger_location
        self.ga_storage_location = storage_location
        self.ga_vbar_location = vbar_location

        # For the state
        self.arch_dbg.state.baddr = storage_location


    def insert_hooks_from_file(self, path):
        spec = importlib.util.spec_from_file_location("concrete_device", path)
        self.hooks_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.hooks_module)

        #Device setup
        if hasattr(self.hooks_module, "device_setup"):
            self.dev = self.hooks_module.device_setup(self)

        #Overwrite required calls
        if hasattr(self.hooks_module, "device_main"):
            self.device_main = self.hooks_module.device_main

    def test_connection(self) -> None:
        self.write(b"PING")
        d = self.read(self.transmission_size)
        if d != b"PONG":
            warning("Invalid response from device: {d}")
        else:
            ok("Connection is working")

    def boot_glitcher(self) -> bool:
        self.write(b"GLIT")
        ret = self.read(4)
        if ret != b"GlAs":
            error("Failed to boot into glitch handler")
            return True
        return False

    def get_stub_location(self) -> int:
        return NotImplemented

    def get_debugger_location(self) -> int:
        return NotImplemented

    def write(self, data) -> None:
        return NotImplemented

    def read(self, len) -> bytes:
        return NotImplemented

    def device_main(self, args) -> None:
        return NotImplemented

    def dump_processor_state(self):
        return NotImplemented

    def add_hook(self, hook_addr, use_smc=True):
        raise NotImplemented

    def sync_state(self):
        '''
        Sync processor state from memory region to registers on device.
        '''
        raise NotImplemented

    def memwrite_io(self, address, data):
        '''
        Write some data byte by byte
        '''
        raise NotImplemented

    def memdump_region(self, offset, size):
        '''
        Dump a region from target device. Based on an offset/address and size:

        Args:

            :param offset: Address of which to dump
            :param size: Size to dump

        Returns:

            Bytes
        '''
        return NotImplemented

    def memdump_region_small(self, offset, size):
        '''
        TODO
        Dump a region from target device. Based on an offset/address and size:

        Args:

            :param offset: Address of which to dump
            :param size: Size to dump

        Returns:

            Bytes
        '''
        return NotImplemented

    def memwrite_region(self, address: int, data: bytes, check: bool):
        '''
        Write a blob of data to an address on the device. Sometimes this function has issues when writing more than 0x20 bytes of data

        Args:

            :param (int): address: Address to write to
            :param (bytes): data: Binary data to write to the device
            :param (Bool): check if data is really written by dumping the region and checking if it has changed
        '''
        return NotImplemented

    def jump_to(self, address):
        return NotImplemented

    def auto_debugger_setup(self):
        return NotImplemented

    def restore_stack_and_jump(self, address, stack : bytes=b""):
        return NotImplemented

    def ping(self):
        self.write(b"PING")
        pong = self.read(4)
        if pong != b"PONG":
            error("Invalid reponse from target!")

    def try_restore_device(self):
        try:
            self.read(0x100)
        except:
            pass
        try:
            self.write(b"PING")
            if self.read(0x100) == b"PONG":
                ok("Restore successful!")
                return True
        except:
            error("Failed to restore debugger connection")
        return False

    def fetch_special_regs(self):
        return NotImplemented

    def copy_functions(self):
        '''
        Copy functions from architecture dependent target to the concrete target class.
        '''
        self.read = self.arch_dbg.read
        self.write = self.arch_dbg.write
        self.memdump_region = self.arch_dbg.memdump_region
        self.memwrite_io = self.arch_dbg.memwrite_io
        # self.memdump_region_small = self.arch_dbg.memdump_region_small
        self.memwrite_region = self.arch_dbg.memwrite_region
        self.get_debugger_location = self.arch_dbg.get_debugger_location
        self.jump_to = self.arch_dbg.jump_to
        self.add_hook = self.arch_dbg.add_hook
        self.auto_debugger_setup = self.arch_dbg.auto_debugger_setup
        self.restore_stack_and_jump = self.arch_dbg.restore_stack_and_jump
        self.sync_state = self.arch_dbg.sync_state
        self.fetch_special_regs = self.arch_dbg.fetch_special_regs

    def reinitialize_device(self):
        self.__init__(self.target_dev, self.connectga)

    def auto_probe_memory(self, start=0, end=12*GB, bs=1 * MB, ss=64, indept=False):
        '''
            Probe region. If there is a timeout, try to restore the connection and move to the next block
            ss = search_size
        '''
        info("probing memory")
        ranges = []
        for current in tqdm.tqdm(range(start, end, bs)):
            try:
                self.memdump_region(current, ss)
                if ranges and ranges[-1].end > current:
                    ranges[-1].size += bs
                    continue

                # Add a memory range
                ranges.append(ConcreteDev_Memory_Segment(current, bs, "UNKNOWN"))
            except Exception:
                if self.try_restore_device():
                    continue
                warn(f"Probing failed at: {current}")
                return ranges


if __name__ == "__main__":
    arg = argparse.ArgumentParser()
    arg.add_argument("device", help="Path to device to connect to")
    arg.add_argument("--connect", help="Connect to the remote GA server", action="store_true", default=False)

    args, unknown = arg.parse_known_args()
    device = ConcreteDevice(args.device, args.connect)
    device.device_main(device, unknown)
