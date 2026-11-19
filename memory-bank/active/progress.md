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
