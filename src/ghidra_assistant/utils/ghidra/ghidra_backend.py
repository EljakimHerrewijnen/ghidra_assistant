import typing, hashlib, struct
from typing import Optional, List, Iterable

class GhidraFunctionBasic():
    def __init__(self, address: str, name: str, args: Optional[List[str]] = None, return_type: Optional[str] = None):
        self.address = address
        self.entry_point = address  # Assuming entry_point is the same as address
        self.name = name
        self.args = args if args is not None else []
        self.return_type = return_type

    def _generate_prototype(self):
        """
        Generate the function prototype based on its name, arguments, and return type.
        """
        args_str = ', '.join(self.args)
        return_type_str = self.return_type if self.return_type else 'void'
        return f"{return_type_str} {self.name}({args_str})"

    @property
    def prototype(self):
        """
        Return the function prototype.
        """
        return self._generate_prototype()

    def __repr__(self):
        return f"<GhidraFunction address={self.address} name={self.name} prototype={self.prototype}>"

class GhidraFunction(GhidraFunctionBasic):
    def __init__(
        self,
        address,
        name,
        args,
        return_type,
        raw_bytes,
        size,
        disassembly,
        decompiled_code=None,
        incoming_functions=None,
        outgoing_functions=None,
        incoming_refs=None,
        outgoing_refs=None,
    ):
        """
        Initialize a GhidraFunction with additional attributes.

        Parameters:
        - address, name, args, return_type: base function info
        - raw_bytes (bytes): function body bytes (best-effort)
        - size (int): size of raw_bytes
        - disassembly (list[str] | Any): disassembly lines or structure
        - decompiled_code (str | None): optional decompiled C
        - incoming_functions / outgoing_functions: legacy names for xref lists
        - incoming_refs / outgoing_refs: preferred names for xref lists
        """
        self.raw_bytes = raw_bytes
        self.size = size
        self.disassembly = disassembly
        self.decompiled_code = decompiled_code

        # Normalize incoming/outgoing reference lists (prefer new names)
        inc = incoming_refs if incoming_refs is not None else incoming_functions
        out = outgoing_refs if outgoing_refs is not None else outgoing_functions
        self.incoming_refs = inc if inc is not None else []
        self.outgoing_refs = out if out is not None else []

        # Initialize the base class with address, name, args, and return_type
        super().__init__(address, name, args, return_type)

    # Backward-compatible aliases
    @property
    def incoming_functions(self):
        return self.incoming_refs

    @property
    def outgoing_functions(self):
        return self.outgoing_refs

    @property
    def unique_id(self) -> str:
        """
        Generate a unique identifier for the function based on its address, size and raw bytes.
        """
        return hashlib.sha256(self.raw_bytes + self.address.encode() + struct.pack("<Q", self.size)).hexdigest()

    @property
    def function_hash(self) -> str:
        """
        Generate a hash of the function's raw bytes.
        """
        return hashlib.sha256(self.raw_bytes).hexdigest()


class Mem:
    def __init__(self, read_mem_fun):
        self.mem_fun = read_mem_fun

    def __getitem__(self, key):
        # Check if 'key' is a slice object
        if isinstance(key, slice):
            # Extract the start, stop, and step attributes of the slice
            start = key.start
            size = key.stop - start

            return self.mem_fun(start, size)
        else:
            # Handle single item access if needed
            return self.mem_fun(key, 1)

    def __setitem__(self, key, value):
        raise Exception("Setting memory is not supported in this backend.")
        # # Check if 'key' is a slice object
        # if isinstance(key, slice):
        #     # Extract the start, stop, and step attributes of the slice
        #     start = key.start
        #     size = key.stop - start

        #     return self.cd.memwrite_region(start, value, True)
        # else:
        #     # Handle single item access if needed
        #     return self.cd.memwrite_region(key, value, True)

class GhidraBackend:
    def __init__(self):
        pass

    if typing.TYPE_CHECKING: # Only for type checking, not at runtime
        @property
        def functions(self) -> Iterable[GhidraFunctionBasic]:
            raise NotImplementedError("This method should be implemented by subclasses.")

        def get_function(self, basicFunction: GhidraFunctionBasic) -> GhidraFunction:
            raise NotImplementedError("This method should be implemented by subclasses.")

        @property
        def all_functions_detailed(self) -> Iterable[GhidraFunction]:
            raise NotImplementedError("This method should be implemented by subclasses.")

        @property
        def cursor(self) -> int:
            raise NotImplementedError("This method should be implemented by subclasses.")





