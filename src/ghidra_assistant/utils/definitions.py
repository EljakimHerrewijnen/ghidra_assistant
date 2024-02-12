from io import BytesIO
import pickle, multiprocessing, sys, tqdm

SNAPSHOT_SAVE_PATH = "bin/"
DEBUGGER_BLOCKSIZE_TRANSMISSION = 0x100

class ConcreteDev_Memory_Segment():
    def __init__(self, address, size, name) -> None:
        '''
            Class that defines memory regions for a concrete device. This should be added during the setup of a concrete device to aid the debugger
        '''
        self.address = address
        self.size = size
        self.name = name

    @property
    def end(self):
        return self.address + self.size

    def in_range(self, address):
        if self.address >= address and address < self.address + self.size:
            return True
        return False

class GA_Memory_Segment():
    def __init__(self, start, end, size, data, name, properties, mmaped_io = False) -> None:
        self.start = start
        self.size = size
        self.end = end
        # Convert bytes to bytesIO object TODO slow
        if type(data) == bytes:
            d = BytesIO()
            d.write(data)
            data = d
        self.data = data
        self.name = name
        self.properties = properties #RWX
        self.mmaped_io = mmaped_io

    def read_all(self):
        self.data.seek(0)
        return self.data.read()

    def read(self, addr, size):
        if addr > self.end or addr < self.start or addr + size > self.end:
            raise NotImplemented("Requested addr and/or size is invalid!")
        self.data.seek(addr - self.start)
        return self.data.read(size)            

    def page_alligned_size(self):
        if self.size % 0x1000 == 0:
            return self.size
        return (self.size // 0x1000 * 0x1000) + 0x1000

    def page_alligned_start(self):
        return self.start + (0x1000 - ((self.start) % 0x1000)) if self.start % 0x1000 else self.start #PAGE ALIGN block

    def mem_in_segment(self, addr):
        if addr > self.start and addr < self.end:
            return True
        return False
        
    def append_segment(self, segment : "GA_Memory_Segment"):
        assert(self.mem_in_segment(segment.start))
        if segment.end > self.end:
            self.end = segment.end
        self.data.seek(segment.start - self.page_alligned_start()) #Should be page alligned
        self.data.write(segment.data)

    def ghidra_to_uc_permissions(self):
        '''
        Convert ghidra permissions to Unicorn/Qiling permissions.
        The permissions are actually the total value inverted for ghidra and UC. So 7 - permissions is enough to get the right permissions.
        '''
        return 7 - self.properties

class GA_Registers():
    #Should be the result form QlRegisterManager .save()
    def __init__(self, registers) -> None:
        self.registers = registers

class GA_Em_Snapshot():
    def __init__(self, memory, registers, arch, mode, bits=32, name = "unnamed", emulator_name = "") -> None:
        self.memory = memory
        self.registers = registers
        self.arch = arch
        self.mode = mode
        self.bits = bits
        self.name = name
        self.emulator_name = emulator_name

    def save(self):
        return pickle.dumps(self)
    
    def save_to_file(self, path):
        if hasattr(path, "write"):
            pickle.dump(self, path)
        else:
            pickle.dump(self, open(path, "wb"))
    
    def get_all_memory(self):
        data = BytesIO()
        for mem in self.memory:
            data.write(mem.data)
        data.seek(0)
        return data.read()
