=====
Setup
=====

To use the GA, install the python requirements in a virtual environment. 

.. code-block:: console

    python3 -m venv venv/
    source venv/bin/activate
    pip3 install -r requirements.txt

Install ``ghidra_bridge`` into ghidra:

.. code-block:: console

    pip3 install ghidra_bridge

(Optional) install ``.pyi`` `bindings in python for ghidra <https://github.com/VDOO-Connected-Trust/ghidra-pyi-generator>`_.

Usage
-----
Open Ghidra and start ghidra_bridge. Next you can run the GA in python.

.. code-block:: console

    python3 ghidra_assistent.py load

VsCode
------

The GA works very well with VsCode. It is *highly* recommended to use vscode.

Android NDK (Optional)
----------------------

To build remote targets, you will need an ``Android NDK``. Download `one from google <https://developer.android.com/ndk/downloads>`_.

Triton (Optional)
-----------------
Follow the instructions at the `offical github page <https://github.com/JonathanSalwan/Triton>`_.

.. note:: 

    If you receive errors while trying to import the triton package (from triton import * ), you will need to copy the triton.so file to the python path (venv/lib/python3.10/site-packages/).

To add python bindings, navigate in the Triton source directory to ``doc/auto_complete`` and run *python3 generate_autocomplete.py*. 
Copy the generated .pyi file to the root of the site-packages folder of your python environment.

Example Devices
---------------
Several example devices are being developed. Most notably:

* https://git.herreweb.nl/EljakimHerrewijnen/Shofel2_T124_python
* https://git.herreweb.nl/EljakimHerrewijnen/Amlogic_S905X3 (Todo, still private)

Unicorn
-------
clone unicorn and build it using:

.. code:: console

    mkdir build; cd build
    cmake .. -DCMAKE_BUILD_TYPE=Release
    make