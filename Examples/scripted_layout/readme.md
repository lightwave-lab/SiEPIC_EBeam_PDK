# Silicon Photonics masks

# Installation

First, you need the `klayout` command line tool. I created a file called `klayout` inside `/usr/local/bin` with these contents:

```
#!/usr/bin/env bash
/Applications/klayout.app/Contents/MacOS/klayout "$@"
```


# Building a mask

Use formulas defines in the Makefile. Type `make` for the default build.


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