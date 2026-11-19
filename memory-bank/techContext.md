# Tech Context

One Python 3 file, no package manager, no dependencies. The installer is POSIX `install.sh`. Native Windows invocation is documented in `WINDOWS.md` as `python memo …`.

## Environment Setup

Python 3 with a working `python3` (POSIX) or `python` (Windows). Git is used at runtime to resolve project scope from `origin` and the checkout root; it is not a build dependency.

## Build Tools

None for the tool. `install.sh` curls `memo` into `~/.optmem`. The `anim/` GIF is a separate Node tree and is not part of the tool.

## Testing Process

`python3 test.py` from the repo root. The suite is a single script of assertions against the `memo` CLI (in-process and subprocess). It isolates `HOME` and `XDG_DATA_HOME` to a temporary directory before loading `memo` (so tests never read or write real stores), and its `run()`/`sub()` helpers automatically assert that printed runnable commands carry valid scope flags. Windows path encodings are asserted on POSIX via `ntpath` (`path_slug` / `repo_slug`); see `WINDOWS.md` for a native smoke with `MEMORY_DIR` set for the global store.
