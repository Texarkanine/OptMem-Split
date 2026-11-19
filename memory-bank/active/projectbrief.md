# Project Brief

## User Story

As an operator running AI coding agents across multiple projects, I want every single-store `memo` command to require an explicit scope flag (`--here` or `--global`) and `MEMORY_DIR` to move only the global memory so that agents stop silently filing global facts into project stores while operators can still place the global store wherever they want on disk.

Reference: [Texarkanine/OptMem-Split#5](https://github.com/Texarkanine/OptMem-Split/issues/5).

## Use-Cases

### Explicit Scope Selection on Store Commands

When an agent runs `note`, `nap`, `recall`, `zoom`, `forget`, `config`, or `import`, it must pass exactly one of `--here` (the project store for `$PWD`) or `--global` (the global store). Passing neither or both fails with a self-explaining stderr message and exit code `1` without touching disk.

### Dual-Memory Wake and Global Init

Bare `wake` continues to read both the global memory and the project memory (global first), even when `MEMORY_DIR` is set. `wake --global` reads only the global memory; `wake --here` is a usage error. `init` always creates the global memory (at `MEMORY_DIR` if set) and accepts and ignores a scope flag.

### Operator-Controlled Storage Locations

`MEMORY_DIR` moves only the global memory (default `~/.optmem/memory`). `XDG_DATA_HOME` governs project memories under `optmem/` (default `~/.local/share`).

### Safe Help Discovery

Passing `-h`, `--help`, or `help` prints module usage to stdout and exits `0` before any store is opened or created.

## Requirements

1. **FR-1 (Scope flag):** `note`, `nap`, `recall`, `zoom`, `forget`, `config`, and `import` require exactly one of `--here` or `--global`, anywhere in argv. Missing or passing both writes nothing, prints one self-explaining message to stderr, and exits `1`.
2. **FR-2 (Unchanged commands):** Bare `wake` reads both memories (global first); `wake --global` reads only global; `init` always creates the global memory and accepts/ignores a scope flag; `note` prints `Saved as #N.`
3. **FR-3 (`MEMORY_DIR` moves only global):** `--global` uses `MEMORY_DIR` when set (default `~/.optmem/memory`); `--here` always uses project memory under `XDG_DATA_HOME` (default `~/.local/share`); bare `wake` reads both memories even when `MEMORY_DIR` is set, reading the resolved global path rather than the `GLOBAL` constant.
4. **FR-5 (`recall` scope):** `recall` searches one memory and requires `--here` or `--global`.
5. **FR-6 (Printed commands carry scope):** `ME` includes ` --here` or ` --global`; the project half of bare `wake` uses ` --here` so every nap prompt, usage line, and "No memories yet" hint carries its scope and runs as printed, except bare `wake`'s paging line stays `memo wake <k> <T>` and `memo --here wake` is a usage error.
6. **FR-8 (Help):** `-h` or `--help` anywhere in argv, or `memo help`, prints module usage (`__doc__`) to stdout and exits `0`.
7. **FR-9 (Setup block):** Update `TEMPLATE` so "While working" shows `note --here` and `note --global`, and `recall`/`zoom` shows both flags.
8. **FR-10 (Read wake whole):** Add to the setup block: "Do not pipe it through `head`, `tail`, or a pager."
9. **FR-11 (Text surfaces):** Align module docstring, setup block (`TEMPLATE` / `install.sh` output), `README.md`, `WINDOWS.md`, and `memory-bank/systemPatterns.md`.
10. **NFR-1..7:** Keep `memo` one stdlib-only Python 3 file; keep diff from upstream small (argv handling, `memory_dir()`, `wake_both()`, setup text); help runs before `store()` and creates nothing; scope error is self-explaining; `test.py` isolates `HOME` and `XDG_DATA_HOME` to temp dirs before its first command; preserve Windows scope resolution and locking; maintain `wake` and `recall` speed.

## Constraints

1. **C-1:** A missing global memory (at `MEMORY_DIR` or default) is an error and is never created except by `init`.
2. **C-2:** A project memory is still created on first write.
3. **C-3:** Only exact `--here`, `--global`, `-h`, or `--help` tokens are flags; all other arguments are data (e.g., `memo note --here --helpiferous` records `--helpiferous`).
4. **C-4:** Breaking change (`feat!:`): release/commit notes must state that calls without a scope flag now fail, and `MEMORY_DIR` now moves only the global memory so project notes go under `XDG_DATA_HOME`.
5. **C-5:** Write the least code that meets the requirements; add no unnamed options.

## Acceptance Criteria

1. FR-1: `memo note "x"` exits `1`, prints the scope error, and leaves `LOG.txt` unchanged.
2. FR-1: `memo note --here --global "x"` exits `1` and changes nothing.
3. FR-1: `memo note --here "x"` appends to project memory; `memo note --global "x"` appends to global memory.
4. FR-1: `nap`, `recall`, `zoom`, `forget`, `config`, and `import` follow the same flag rules as `note`.
5. FR-2: `memo init` works with no flag, `--here`, or `--global`, and always creates the global memory, at `MEMORY_DIR` if set.
6. FR-3: With `MEMORY_DIR` set, `--global` uses it, `--here` uses project memory under `XDG_DATA_HOME`, and bare `wake` prints both memories.
7. FR-3, C-1: With `MEMORY_DIR` set to a missing directory, `--global` commands fail and create nothing.
8. C-3: `memo note --here --helpiferous` records `--helpiferous`.
9. FR-6: `memo --here wake` exits `1` and changes nothing; bare `wake`'s paging line is still `memo wake <k> <T>`.
10. FR-5: `memo recall --here PATTERN` and `memo recall --global PATTERN` search that one memory.
11. FR-2, FR-6: Bare `wake` output matches today except commands printed for the project memory contain `--here`.
12. FR-6: Every command printed by a nap prompt contains `--here` or `--global`, and runs as printed.
13. FR-8, NFR-3: `memo note --help`, `memo --help`, `memo -h`, and `memo help` print usage to stdout, exit `0`, leave every store unchanged, and create no store in a fresh project.
14. FR-9, FR-10, FR-11: Every listed text surface matches the new rules.
15. NFR-5: `test.py` sets `HOME` and `XDG_DATA_HOME` to temporary directories before its first command and leaves real stores unchanged.
16. `test.py` covers each criterion above.
17. C-4: The breaking change commit uses `feat!:` with both required breaking-change notes.
