# Ghidra Assistant
**Contains lots of bugs!**

This is the result of several scripts merged into a single package that I reuse often. Usually in combination with my [Gupje](https://github.com/EljakimHerrewijnen/Gupje) debugger and [ghidra](https://github.com/NationalSecurityAgency/ghidra).

## Development with PDM
This project uses PDM for packaging and dependency management.

- Install PDM (one-time):
	- Linux/macOS: `curl -sSL https://pdm-project.org/install-pdm.py | python3 -`
	- Or via pipx: `pipx install pdm`

- Create and sync the environment:
```bash
pdm sync -d
```

- Run the package (module):
```bash
pdm run python -m ghidra_assistant.ghidra_assistant
```

- Use the console script:
```bash
pdm run ghidra-assistant
```

- Build wheels/sdist:
```bash
pdm build
```
