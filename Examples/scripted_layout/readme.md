# Silicon Photonics masks

# Installation

First, you need the `klayout` command line tool. I created a file called `klayout` inside `/usr/local/bin` with these contents:

```
#!/usr/bin/env bash
/Applications/klayout.app/Contents/MacOS/klayout "$@"
```

# Install SiEPIC-Tools

This assumes that you have a Developer's installation of SiEPIC-Tools in the v0.4.0 branch (this script was tested with commit 9ab51adb23cabf52429cbfa60f763e83cd4e09cc: https://github.com/lukasc-ubc/SiEPIC-Tools/tree/9ab51adb23cabf52429cbfa60f763e83cd4e09cc)

In order for python to see the package "SiEPIC", you need to include its path into the PYTHONPATH variable. Type the following to do so:

```bash
export PYTHONPATH="/path/to/SiEPIC-Tools/klayout_dot_config/python:$PYTHONPATH"
```

# Building a mask

Use formulas defined in the Makefile. Type `make` for the default build.

`make from_klayout`, `make from_klayout_batch_mode` and `make from_python` now all work, but they require a newer version of SiEPIC-Tools than listed above. This code was tested with commit hash 26c38fc63fc2221854fab56152277bb1bd410f2e https://github.com/lukasc-ubc/SiEPIC-Tools/tree/26c38fc63fc2221854fab56152277bb1bd410f2e (branch self-testing)

# Testing

You must first `pip install lytest`, which combines `pytest` with geometry change detection. Right now, the layout can only be built by the klayout interpreter. You can either run pytest from klayout interpreter

```shell
make test
```

to look at cell-level layout, or you can have pytest call klayout interpreter from shell

```shell
pytest .
```

to look at script-level layout.
