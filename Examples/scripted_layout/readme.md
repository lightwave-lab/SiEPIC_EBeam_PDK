# Silicon Photonics masks

# Installation

First, you need the `klayout` command line tool. I created a file called `klayout` inside `/usr/local/bin` with these contents: 

```
#!/usr/bin/env bash
/Applications/klayout.app/Contents/MacOS/klayout "$@"
```


# Building a mask

Use formulas defines in the Makefile. Type `make` for the default build.
