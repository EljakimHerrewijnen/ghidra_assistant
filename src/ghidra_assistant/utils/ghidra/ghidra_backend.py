class GhidraFunctionBasic():
    def __init__(self, address: str, name: str, args: list = None, return_type: str = None):
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
    def __init__(self, address, name, args, return_type, raw_bytes, size, disassembly):
        """
        Initialize a GhidraFunction with additional attributes.
        """
        self.raw_bytes = raw_bytes
        self.size = size
        self.disassembly = disassembly

        # Initialize the base class with address, name, args, and return_type
        super().__init__(address, name, args, return_type)


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

    # @property
    # def functions(self) -> list[GhidraFunctionBasic]:
    #     raise NotImplementedError("This method should be implemented by subclasses.")

    # def get_function(self, basicFunction : GhidraFunctionBasic) -> GhidraFunction:
    #     raise NotImplementedError("This method should be implemented by subclasses.")

    # def get_all_functions(self) -> list[GhidraFunction]:
    #     raise NotImplementedError("This method should be implemented by subclasses.")

    # @property
    # def cursor(self) -> int:
    #     raise NotImplementedError("This method should be implemented by subclasses.")
