# Progress

Implement [Texarkanine/OptMem-Split#5](https://github.com/Texarkanine/OptMem-Split/issues/5): require explicit `--here` or `--global` scope on single-store commands, limit `MEMORY_DIR` to the global store, add `-h`/`--help`/`help`, keep printed commands scoped and runnable, isolate `test.py`, and align all documentation surfaces.

**Complexity:** Level 2

## 2026-11-19 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Fetched issue #5 and confirmed intent with operator
    - Read `memo`, `install.sh`, `README.md`, `WINDOWS.md`, and persistent memory-bank files
    - Classified task as Level 2 and initialized ephemeral memory-bank files
* Decisions made
    - Level 2 selected: single-file CLI enhancement with fully specified requirements and no open architectural redesign
* Insights
    - Current working branch is `txrk9.multi-store-filing` at `be43de4` (`main.split`)
    - `test.py` currently relies on `MEMORY_DIR` to isolate calls until line 640 and omits `--here`/`--global` on store commands; it must isolate `HOME` and `XDG_DATA_HOME` upfront

## 2026-11-19 - PLAN - COMPLETE

* Work completed
    - Surveyed `memo`, `test.py`, `install.sh`, `README.md`, `WINDOWS.md`, `relink-path-stores`, and `memory-bank/`
    - Produced TDD test plan, linear implementation plan, challenges/mitigations, and pre-mortem in `memory-bank/active/tasks.md`
    - Updated `memory-bank/active/activeContext.md`
* Decisions made
    - Separate `wake_cmd()` (bare for project, `--global` for global) from `ME` (`--here` for project, `--global` for global) so `wake` recovery/paging lines stay runnable without `--here`
    - Set `ME = pretty(__file__) + " --global"` during `init` so the generated global `config` header prints a runnable `--global config` hint
    - Route `test.py`'s in-process `run()` through `cli.main()` and isolate `HOME`/`XDG_DATA_HOME` at top of file before loading `memo`
* Insights
    - `cmd_zoom()` line 894 also prints `Run: %s wake` and would print illegal `--here wake` unless it uses `wake_cmd()`
    - `store()` must drop `os.environ.get("MEMORY_DIR") or` from its missing-dir guard and check `if SCOPE_GLOBAL:` only, or `--here` would fail to create new project stores when `MEMORY_DIR` is set

