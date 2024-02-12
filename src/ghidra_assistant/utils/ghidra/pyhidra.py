import pyhidra


import typing
if typing.TYPE_CHECKING:
    import ghidra
    from ghidra.ghidra_builtins import *

class PyHidra():
    def __init__(self) -> None:
        pyhidra.start()
        from ghidra.app.util.headless import HeadlessAnalyzer
        from ghidra.program.flatapi import FlatProgramAPI
        from ghidra.base.project import GhidraProject
        from java.lang import String
        pass