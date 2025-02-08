import ghidra_bridge
from ...utils.ghidra.pyhidra import *
from ..utils import *
from ..definitions import *
import typing
if typing.TYPE_CHECKING:
    import ghidra
    from ghidra.ghidra_builtins import *


# actual code follows here
from tqdm import tqdm
from io import BytesIO
import ast

class VarVisitor(ast.NodeVisitor):
    """
    Simple visitor that gathers all variable names from an AST
    """
    def __init__(self):
        super(VarVisitor, self).__init__()
        self.variables = set()

    def visit_Name(self, node):
        self.variables.add(node.id)

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

uc_ghidra_arch_translation = {
    'ARM'       : 'ARM',
    'AARCH64'   : 'ARM64',
    'RISCV'     : 'RISCV'
}

uc_ghidra_mode_translation = {
    'little'    : "EL",
    'big'       : "EB"
}

class Ghidra:
    def __init__(self, use_ghidra_bridge=True):
        if not use_ghidra_bridge:
            # pyhidra()
            pass # TODO add pyhidra as scripting backend. Issues with running ghidra instance.
        else:
            self.ns = AttrDict()  # Create our own namespace to keep junk out of the global one
        if typing.TYPE_CHECKING:
            pass
        else:
            self.bridge = ghidra_bridge.GhidraBridge(namespace=globals(), response_timeout=100)
            self.tool = state.getTool()
        self.codevwr_svc = self.tool.getService(ghidra.app.services.CodeViewerService)
        self.listing_pnl = self.codevwr_svc.getListingPanel()

        if currentProgram is not None:
            # Setup flatapi
            self.fpapi = ghidra.program.flatapi.FlatProgramAPI(currentProgram)

            # When no code is initialized
            self.function_mgr = currentProgram.getFunctionManager()
            self._reg_tmode = currentProgram.getRegister('TMode')
            self.address_factory = currentProgram.getAddressFactory()
            self.data_type_manager = currentProgram.getDataTypeManager()
            self.listing = currentProgram.getListing()
            self.memory = currentProgram.getMemory()
            self.symbol_manager = currentProgram.getSymbolTable()
            self._name = currentProgram.name
            self.address_space = self.address_factory.getDefaultAddressSpace()

            # Decompiler
            self.ifc = ghidra.app.decompiler.DecompInterface()
            self.ifc.openProgram(currentProgram)

        self.state = getState()
        self.project = self.state.getProject()
        self.program = self.state.getCurrentProgram()
        self.locator = self.project.getProjectData().getProjectLocator()

    # eval magic from https://github.com/fmagin/ipyghidra
    def remote_eval(self, code):
        code = code.replace("\n", "")
        code = str(code)
        print(code)
        # Parse the AST and gather all variable names used
        code_ast = ast.parse(code)
        v = VarVisitor()
        v.visit(code_ast)
        # For every variable in the AST check if it is defined in the current user namespace and if yes get its actual value
        ns = globals()
        vars = {var: ns[var] for var in  v.variables if var in ns}
        # This mapping from variable names to objects can now be passed to remote_eval which makes sure those variables exist when evaluating on the server side
        return self.bridge.remote_eval(code, **vars)

    def get_name(self):
        return self.locator.getName() + "_" + self._name

    def get_arch(self):
        return uc_ghidra_arch_translation[currentProgram.getCompilerSpec().getLanguage().toString().split('/')[0]]

    def get_mode(self):
        return uc_ghidra_mode_translation[currentProgram.getLanguage().getLanguageDescription().getEndian().toString()]

    def get_bits(self):
        return currentProgram.getLanguage().getLanguageDescription().getSize()

    def _jaddr(self, addr):
        # The string that's fed to getAddress NEEDS to be hex for some godawful reason
        return self.address_factory.getAddress(hex(addr))

    def _jbytes(self, dat):
        return bytes(dat)

    def startTransaction(self, name):
        self.stopTransaction()
        self.transaction = currentProgram.startTransaction(name)

    def stopTransaction(self):
        if hasattr(self, "transaction"):
            currentProgram.endTransaction(self.transaction, True)

    def set_background_color(self, addresses, color="java.awt.Color.YELLOW"):
        '''
        Highlight a list of addresses
        '''
        tr = currentProgram.startTransaction(f"Coloring lines")
        d = self.bridge.remote_eval("[currentProgram.getAddressFactory().getAddress(addr) for addr in addresses]", addresses=[hex(addr) for addr in addresses])
        self.bridge.remote_eval(f"[setBackgroundColor(addr, {color}) for addr in d]", d=d)
        currentProgram.endTransaction(tr, True)

    def clear_background_color(self):
        '''
        Clears all background colors
        '''
        self.bridge.remote_eval("[clearBackgroundColor(addr) for addr in currentProgram.getMemory().getAllInitializedAddressSet().getAddresses(start, True)]", start=self._jaddr(0))

    @property
    def cursor(self):
        return self.listing_pnl.getCursorLocation().address.offset

    @cursor.setter
    def cursor(self, addr, goto=True):
        self.listing_pnl.setCursorPosition(ghidra.program.util.ProgramLocation(currentProgram, self._jaddr(addr)))
        if goto:
            self.listing_pnl.goTo(self._jaddr(addr))

    def get_function_name_by_address(self, addr):
        addr = self._jaddr(addr) if type(addr) == int else addr
        return self.function_mgr.getFunctionContaining(addr)

    def get_function_by_name(self, name):
        if currentProgram is None:
            return 0x0
        start = self.symbol_manager.getLabelOrFunctionSymbols(name, None)
        if len(start) > 0:
            return [0].getProgramLocation().address.offset
        return 0x0

    def _jarray2bytes(self, jarray):
        return bytes(map(ord, jarray.tostring()))

    def read_mem_block(self, blk, chunk_size=128*1024):
        h_data = blk.getData()
        b_data = BytesIO()
        sz = blk.getSize()
        p = tqdm.tqdm(total=sz, unit_scale=1, unit=' bytes')
        for _ in range(0, sz, chunk_size):
            b_data.write(self._jarray2bytes(h_data.readNBytes(chunk_size)))
            p.update(chunk_size)
        p.refresh()
        b_data.seek(0)
        return b_data

    def is_thumb(self, addr):
        if currentProgram is None:
            return False
        tmode_val = currentProgram.programContext.getRegisterValue(self._reg_tmode, toAddr(addr))
        return bool(tmode_val.unsignedValueIgnoreMask)

    def get_ghidra_memory_maps_r(self) -> []:
        '''
        Download memory maps with remote eval. Which is much, much faster than the old way.

        Returns:
            [GA_Memory_Segment]
        '''
        memory = self.bridge.remote_eval("[(s.getStart().offset, s.getEnd().offset, s.getSize(), s.comment, s.name, s.permissions, s.getData().readNBytes(s.getSize())) for s in currentProgram.getMemory().blocks]")
        memory_maps = []
        for s in memory:
            start = s[0]
            end = s[1]
            size = s[2]
            comment = s[3]
            name = s[4]
            permissions = s[5]
            content = self._jarray2bytes(s[6])

            if comment is not None:
                if "[not-loaded]" in comment or "[" not in comment:
                    #Skip not loaded mappings.
                    continue

            mem = GA_Memory_Segment(start, end, size, content, name, permissions)
            memory_maps.append(mem)
        return memory_maps

    def get_ghidra_memory_maps(self):
        return self.get_ghidra_memory_maps_r()

    def get_entry_point(self):
        return self.symbol_manager.getLabelOrFunctionSymbols('_entry', None)

    def get_memory_block(self, addr):
        for block in self.memory.getBlocks():
            if block.contains(toAddr(addr)):
                return block
        return None

    def is_region_available(self, start, end):
        print(f"start={hex(start)}|end={hex(end)}")
        for block in self.memory.getBlocks():
            b_start = int(block.start.toString(), 16)
            b_end = int(block.end.toString(), 16)

            # Check if block is in this block
            if start >= b_start and end <= b_end:
                return False

            # check if start overlaps
            if start >= b_start and start <= b_end:
                return False

            # check if end overlaps
            if end >= b_start and end <= b_end:
                return False

        return True

    def add_memory(self, data, addr, overwrite, name, overwrite_content = False):
        start = addr
        end = addr + len(data)

        tr = currentProgram.startTransaction(f"Adding memory {name}: start={hex(start)} end={hex(end)}")

        available = self.is_region_available(start, end)
        if not available and overwrite:
            block = self.get_memory_block(start)
            if block is None:
                warn("Invalid block!")
                currentProgram.endTransaction(tr, True)
                return
            # warn(f"Removing memory {block.name}: start={hex(block.start)} end={hex(block.end)}")
            self.memory.removeBlock(block, monitor)
            while not self.is_region_available(start, end):
                continue
            self.memory.createInitializedBlock(name, toAddr(start), len(data), 0, monitor, False)
        elif not available and overwrite_content:
            info("Region already mapped. Overwriting data...")
            currentProgram.endTransaction(tr, True)
            return
        elif not available:
            info("Region already mapped. Skipping.")
            currentProgram.endTransaction(tr, True)
            return
        elif available:
            # Available, create block
            info(f"Adding memory {name}: start={hex(start)} end={hex(end)}")
            self.memory.createInitializedBlock(name, toAddr(start), len(data), 0, monitor, False)

        #Otherwise mmap and write it.

        #name: unicode, start: ghidra.program.model.address.Address, fileBytes: ghidra.program.database.mem.FileBytes, offset: long, size: long, overlay: bool) -> ghidra.program.model.mem.MemoryBlock:
        self.memory.setBytes(toAddr(start), bytes(data))
        currentProgram.endTransaction(tr, True)

    def mmap_region(self, addr, name, size, read=True, write=True, execute=False):
        tr = currentProgram.startTransaction(f"Mapping memory region {name} at {hex(addr)}")
        self.memory.createInitializedBlock(name, toAddr(addr), size, 0, monitor, False)
        block = self.memory.getBlock(toAddr(hex(addr)))
        block.setPermissions(read, write, execute)
        currentProgram.endTransaction(tr, True)

    def write_mem(self, addr, data):
        '''
        write data to memory, if region is available
        '''
        # check if address is in a block
        block = self.get_memory_block(addr)
        if block is None:
            warn(f"Address {hex(addr)} is not in a block")
            return
        # check if len(data) is too big
        if len(data) > block.getSize():
            warn(f"Data is too big for block {block.name}")
            return
        tr = currentProgram.startTransaction(f"Writing memory at {hex(addr)}")
        self.memory.setBytes(toAddr(addr), bytes(data))
        currentProgram.endTransaction(tr, True)

    def get_memory_block(self, addr):
        for block in self.memory.getBlocks():
            if block.contains(toAddr(hex(addr))):
                return block
        return None

    def get_function_decompiled_code(self, func):
        # decompile the function and print the pseudo C
        results = self.ifc.decompileFunction(func, 0, ghidra.util.task.ConsoleTaskMonitor())
        return results.getDecompiledFunction().getC()

    def get_all_structures(self):
        # self.data_type_manager.addDataType()
        '''
        data_type = StructureDataType(category.getCategoryPath(), struct_name, 0)
        data_type.add(int32_t, 4, "len", None)
        data_type.add(int32_t, 4, "reserved", None)

        return category.addDataType(data_type, None)
        '''
        return self.data_type_manager.getAllStructures()

    def rename_function(self, addr, name):
        '''
        Rename a function on an address. Return True if succes, else False.
        TODO create remote eval
        '''

        tr = currentProgram.startTransaction(f"Naming function {hex(addr)} to {name}")
        addr = self._jaddr(addr)
        existing_function = self.listing.getFunctionContaining(addr)
        if existing_function is None:
            # Try to create it
            self.fpapi.createFunction(addr, name)
            currentProgram.endTransaction(tr, True)
            return True
        existing_function.setName(name, ghidra.program.model.symbol.SourceType.DEFAULT)
        currentProgram.endTransaction(tr, True)
        return True

    def get_all_functions(self):
        # TODO add remote eval to speed up this process
        # name_list = self.bridge.remote_eval("[ f.getName() for f in currentProgram.getFunctionManager().getFunctions(True)]")
        func = currentProgram.getFunctionManager().getFunctions(True).next()
        # mnemonics = self.bridge.remote_eval("[ i.getMnemonicString() for i in currentProgram.getListing().getInstructions(f.getBody(), True)]", f=func)
        # print(mnemonics)
        res = self.remote_eval("[f.body for f in currentProgram.getFunctionManager().getFunctions(True)]")

        print(res)
        funcs : ghidra.program.model.listing.FunctionIterator = self.function_mgr.getFunctions(True)

        for func in funcs:
            func : ghidra.program.database.function.FunctionDB = func
            func_name = func.name
            print(func_name)
            # func_addr = func.getEntryPoint()
            # addrSet = func.getBody()
            # codeUnits = self.listing.getCodeUnits(addrSet, True) # true means 'forward'

            # for codeUnit in codeUnits:
            #     print(f"{codeUnit.getAddress()} : {self._jarray2bytes(codeUnit.getBytes()).hex()} : {codeUnit.toString()}")
	        #     print("0x{} : {:16} {}".format(codeUnit.getAddress(), hex(codeUnit.getBytes()), codeUnit.toString()))

            # func_decompiled = self.get_function_decompiled_code(func)

            # addrSet = func.getBody()
            # codeUnits = self.listing.getCodeUnits(addrSet, True)
            # GA_Code_block()

    def get_all_functions_r(self):
        code2 = self.bridge.remote_eval("""
            [
                (

                )
                for f in currentProgram.getFunctionManager().getFunctions(True)
            ]
        """)
        for name in code2:
            print("0x" + name[0], name[1])
            # print(name)