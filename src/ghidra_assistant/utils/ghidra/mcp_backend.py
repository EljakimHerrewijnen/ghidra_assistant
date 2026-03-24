from .ghidra_backend import *
from typing import Iterable, Optional, Any, Dict, List
import sys
try:
    import requests  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    requests = None  # type: ignore
import argparse
import logging
from urllib.parse import urljoin


DEFAULT_GHIDRA_SERVER = "http://127.0.0.1:8192/"

logger = logging.getLogger(__name__)

# Initialize ghidra_server_url with default value
ghidra_server_url = DEFAULT_GHIDRA_SERVER

def safe_get(endpoint: str, params: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    Perform a GET request with optional query parameters.
    """
    if params is None:
        params = {}

    url = urljoin(ghidra_server_url, endpoint)

    try:
        if requests is None:
            return ["Error: 'requests' package is not installed"]
        response = requests.get(url, params=params, timeout=5)
        response.encoding = 'utf-8'
        if response.ok:
            return response.text.splitlines()
        else:
            return [f"Error {response.status_code}: {response.text.strip()}"]
    except Exception as e:
        return [f"Request failed: {str(e)}"]

def safe_post(endpoint: str, data: Dict[str, Any] | str) -> str:
    try:
        url = urljoin(ghidra_server_url, endpoint)
        if requests is None:
            return "Error: 'requests' package is not installed"
        if isinstance(data, dict):
            response = requests.post(url, data=data, timeout=5)
        else:
            response = requests.post(url, data=data.encode("utf-8"), timeout=5)
        response.encoding = 'utf-8'
        if response.ok:
            return response.text.strip()
        else:
            return f"Error {response.status_code}: {response.text.strip()}"
    except Exception as e:
        return f"Request failed: {str(e)}"

def list_methods(offset: int = 0, limit: int = 100) -> list:
    """
    List all function names in the program with pagination.
    """
    return safe_get("methods", {"offset": offset, "limit": limit})

def list_classes(offset: int = 0, limit: int = 100) -> list:
    """
    List all namespace/class names in the program with pagination.
    """
    return safe_get("classes", {"offset": offset, "limit": limit})

def decompile_function(name: str) -> str:
    """
    Decompile a specific function by name and return the decompiled C code.
    """
    return safe_post("decompile", name)

def rename_function(old_name: str, new_name: str) -> str:
    """
    Rename a function by its current name to a new user-defined name.
    """
    return safe_post("renameFunction", {"oldName": old_name, "newName": new_name})

def rename_data(address: str, new_name: str) -> str:
    """
    Rename a data label at the specified address.
    """
    return safe_post("renameData", {"address": address, "newName": new_name})

def list_segments(offset: int = 0, limit: int = 100) -> list:
    """
    List all memory segments in the program with pagination.
    """
    return safe_get("segments", {"offset": offset, "limit": limit})

def list_imports(offset: int = 0, limit: int = 100) -> list:
    """
    List imported symbols in the program with pagination.
    """
    return safe_get("imports", {"offset": offset, "limit": limit})

def list_exports(offset: int = 0, limit: int = 100) -> list:
    """
    List exported functions/symbols with pagination.
    """
    return safe_get("exports", {"offset": offset, "limit": limit})

def list_namespaces(offset: int = 0, limit: int = 100) -> list:
    """
    List all non-global namespaces in the program with pagination.
    """
    return safe_get("namespaces", {"offset": offset, "limit": limit})

def list_data_items(offset: int = 0, limit: int = 100) -> list:
    """
    List defined data labels and their values with pagination.
    """
    return safe_get("data", {"offset": offset, "limit": limit})

def search_functions_by_name(query: str, offset: int = 0, limit: int = 100) -> list:
    """
    Search for functions whose name contains the given substring.
    """
    if not query:
        return ["Error: query string is required"]
    return safe_get("searchFunctions", {"query": query, "offset": offset, "limit": limit})

def rename_variable(function_name: str, old_name: str, new_name: str) -> str:
    """
    Rename a local variable within a function.
    """
    return safe_post("renameVariable", {
        "functionName": function_name,
        "oldName": old_name,
        "newName": new_name
    })

def get_function_by_address(address: str) -> str:
    """
    Get a function by its address.
    """
    return "\n".join(safe_get("get_function_by_address", {"address": address}))

def get_function_containing_address(address: str) -> str:
    """
    Get the function that contains the specified address.
    """
    return "\n".join(safe_get("get_function_containing_address", {"address": address}))

def get_current_address() -> str:
    """
    Get the address currently selected by the user.
    """
    return "\n".join(safe_get("get_current_address"))

def get_current_function() -> str:
    """
    Get the function currently selected by the user.
    """
    return "\n".join(safe_get("get_current_function"))

def list_functions() -> list:
    """
    List all functions in the database.
    """
    return safe_get("list_functions")

def decompile_function_by_address(address: str) -> str:
    """
    Decompile a function at the given address.
    """
    return "\n".join(safe_get("decompile_function", {"address": address}))

def disassemble_function(address: str) -> list:
    """
    Get assembly code (address: instruction; comment) for a function.
    """
    return safe_get("disassemble_function", {"address": address})

def set_decompiler_comment(address: str, comment: str) -> str:
    """
    Set a comment for a given address in the function pseudocode.
    """
    return safe_post("set_decompiler_comment", {"address": address, "comment": comment})

def set_disassembly_comment(address: str, comment: str) -> str:
    """
    Set a comment for a given address in the function disassembly.
    """
    return safe_post("set_disassembly_comment", {"address": address, "comment": comment})

def rename_function_by_address(function_address: str, new_name: str) -> str:
    """
    Rename a function by its address.
    """
    return safe_post("rename_function_by_address", {"function_address": function_address, "new_name": new_name})

def set_function_prototype(function_address: str, prototype: str) -> str:
    """
    Set a function's prototype.
    """
    return safe_post("set_function_prototype", {"function_address": function_address, "prototype": prototype})

def set_local_variable_type(function_address: str, variable_name: str, new_type: str) -> str:
    """
    Set a local variable's type.
    """
    return safe_post("set_local_variable_type", {"function_address": function_address, "variable_name": variable_name, "new_type": new_type})

def get_xrefs_to(address: str, offset: int = 0, limit: int = 100) -> list:
    """
    Get all references to the specified address (xref to).

    Args:
        address: Target address in hex format (e.g. "0x1400010a0")
        offset: Pagination offset (default: 0)
        limit: Maximum number of references to return (default: 100)

    Returns:
        List of references to the specified address
    """
    return safe_get("xrefs_to", {"address": address, "offset": offset, "limit": limit})

def get_xrefs_from(address: str, offset: int = 0, limit: int = 100) -> list:
    """
    Get all references from the specified address (xref from).

    Args:
        address: Source address in hex format (e.g. "0x1400010a0")
        offset: Pagination offset (default: 0)
        limit: Maximum number of references to return (default: 100)

    Returns:
        List of references from the specified address
    """
    return safe_get("xrefs_from", {"address": address, "offset": offset, "limit": limit})

def get_function_xrefs(name: str, offset: int = 0, limit: int = 100) -> list:
    """
    Get all references to the specified function by name.

    Args:
        name: Function name to search for
        offset: Pagination offset (default: 0)
        limit: Maximum number of references to return (default: 100)

    Returns:
        List of references to the specified function
    """
    return safe_get("function_xrefs", {"name": name, "offset": offset, "limit": limit})

def list_strings(offset: int = 0, limit: int = 2000, filter: Optional[str] = None) -> list:
    """
    List all defined strings in the program with their addresses.

    Args:
        offset: Pagination offset (default: 0)
        limit: Maximum number of strings to return (default: 2000)
        filter: Optional filter to match within string content

    Returns:
        List of strings with their addresses
    """
    params: Dict[str, Any] = {"offset": offset, "limit": limit}
    if filter:
        params["filter"] = filter
    return safe_get("strings", params)

def read_memory(address, size: int = 2000) -> str:
    """
    Get raw bytes from the specified address.

    Args:
        address: Address to read from in hex format (e.g. "0x1400010a0") or an int
        size: Number of bytes to read (default: 2000)

    Returns:
        Raw bytes as a space-separated hex string
    """
    if isinstance(address, int):
        address = hex(address)

    assert isinstance(address, str), "Address must be a string in hex format (e.g. '0x1400010a0')"
    params = {"address": address, "size": size}
    dat = safe_get("memory", params)

    # ['0xfd', '0xff', '0xff', '0xff', '0x25', '0x81', '0xf1', '0x3b', '0x99', '0xa3']
    # convert to bytes
    if len(dat) == 0:
        return ""
    # Join any returned hex tokens into a single space-separated string
    return " ".join(dat)

def get_program_info() -> str:
    """
    Get basic information about the current program.
    """
    return safe_get("program_info")[0] if safe_get("program_info") else "No program information available."

class MCPBackend(GhidraBackend):
    """Backend that talks to the simple HTTP MCP server.

    This wraps the existing module-level request helpers and tool functions in a
    cleaner, property-based interface consistent with other backends.
    """

    def __init__(self):
        super().__init__()

        # Bind memory access through an instance method for consistency
        self.mem = Mem(self.read_memory)

    # -------- Memory --------
    def read_memory(self, address, size: int = 2000) -> bytes:
        """Read memory bytes at address.

        Accepts int or hex-string address and returns bytes.
        """
        if isinstance(address, int):
            address = hex(address)

        assert isinstance(address, str), "Address must be a string in hex format (e.g. '0x1400010a0')"

        params = {"address": address, "size": size}
        dat = safe_get("memory", params)

        if len(dat) == 1:
            # Error string passthrough to empty bytes for consistency
            try:
                return bytes(int(x, 16) for x in dat if x.startswith('0x'))
            except Exception:
                return b""
        elif len(dat) == 0:
            return b""
        else:
            return bytes(int(x, 16) for x in dat if x.startswith('0x'))

    def write_mem(self, address, data: bytes) -> None:
        """Write memory if the server supports it (not implemented here)."""
        raise NotImplementedError("write_mem is not supported by MCP backend")

    @property
    def program_info(self):
        """
        Get basic information about the current program.
        """
        return get_program_info()

    @property
    def functions(self) -> Iterable[GhidraFunctionBasic]:
        """
        Generator that yields basic function descriptors from the program.
        """
        for f in list_functions():
            address = f.split(' ')[-1]
            name = f.split(' at ')[0]
            yield GhidraFunctionBasic(address, name)

    def get_function(self, basicFunction: GhidraFunctionBasic) -> GhidraFunction:
        """
        Get a GhidraFunction object for a given basic function.
        """
        address = basicFunction.address
        name = basicFunction.name

        # 'Function: FUN_00000410 at 00000410\nSignature: undefined FUN_00000410(void)\nEntry: 00000410\nBody: 00000410 - 0000045f'
        fun_details = get_function_by_address(basicFunction.address)
        if fun_details == 'No function found at address 0':
            raise ValueError(f"Function {name} at address {address} not found.")
        # Parse the function details to extract the prototype and other information
        entry_point = int(fun_details.split('\n')[2].split(': ')[1].strip(), 16)

        # Body: 00000410 - 0000045f
        size = int(fun_details.split('\n')[3].split(': ')[1].strip().split(" - ")[1], 16) - int(fun_details.split('\n')[3].split(': ')[1].strip().split(" - ")[0], 16) + 1 #Add one since it will not count the last byte

        # Fetch additional details for the function
        disassembly = disassemble_function(address)
        incoming_functions = get_function_xrefs(name)
        outgoing_functions = get_xrefs_from(address)

        raw_bytes = self.mem[entry_point:entry_point + size]
        size = len(raw_bytes)

        return GhidraFunction(
            address,
            name,
            [],
            None,
            raw_bytes,
            size,
            disassembly,
            decompiled_code=None,
            incoming_refs=incoming_functions,
            outgoing_refs=outgoing_functions,
        )

    @property
    def all_functions_detailed(self) -> Iterable[GhidraFunction]:
        """
        Get all functions in the program.
        """
        for f in self.functions:
            yield self.get_function(f)

    @property
    def cursor(self) -> int:
        cur = get_current_address().strip()
        # int(..., 16) accepts both with and without 0x prefix
        return int(cur, 16)

    def get_function_by_address(self, address: str) -> GhidraFunction:
        """
        Get a function by its address.
        """
        basic_function = GhidraFunctionBasic(address, "")
        return self.get_function(basic_function)

    def get_function_containing_address(self, address: str) -> GhidraFunctionBasic:
        """
        Get the function that contains the specified address.
        """
        # 'Function: bootloader_init at 000804a4\nSignature: undefined bootloader_init(void)'
        f = get_function_containing_address(address)
        address = f.split(' ')[3].split("\n")[0]
        name = f.split(' ')[1]
        return GhidraFunctionBasic(address, name)

    # Build a property memory that is a list that will query the backend for the memory

