Introduction to the Ghidra Assistant
====================================
The ghidra assistant(GA) is a tool that tries to, easily incoperate several functions in ghidra that are currently missing. The main things I miss in ghidra currently are:

    * Easy programming interface with gui that does not rely on python2 or java. 
    * Easily interact with emulators and debuggers. gdb can be used, but not qiling, qemu or panda. I would like to use all of them
    * Incoperate symbolic execution(Triton, Angr) as a standard tool in ghidra. 
    * Fuzzing with symbolic execution and concrete execution. It would be nice to have an easy method of debugging concrete targets(avatar-gdb).
    * Easily add c structures to ghidra. The current method in ghidra is a pain, I would like something that will use a linter to import a lot of structures from an opensource project (preferably all)

Other wanted features:
**********************
    -   Interactive assembly debugger
    -   Pagetable parsing 

This list will probably only keep growing.




