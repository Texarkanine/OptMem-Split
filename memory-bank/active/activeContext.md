# Active Context

## Current Task: require-scope-flag
**Phase:** PREFLIGHT - COMPLETE (PASS WITH ADVISORY)

## What Was Done
- Audited every function, `ME` interpolation, and `MEMORY_DIR`/`SCOPE_GLOBAL` reference across `memo`, `test.py`, `install.sh`, `README.md`, `WINDOWS.md`, `relink-path-stores`, and `memory-bank/`.
- Produced complete TDD test plan, linear implementation plan, challenges/mitigations, and pre-mortem in `memory-bank/active/tasks.md`.
- Identified subtle edge cases: `wake_cmd()` separation from `ME` (in both `cmd_wake()` and `cmd_zoom()`), `ME` scoping during `cmd_init` for `write_config()`, removing `os.environ.get("MEMORY_DIR")` from `store()`'s missing-directory guard so `--here` still creates project stores when `MEMORY_DIR` is set, and routing `test.py`'s `run()` through `cli.main()` with upfront `HOME`/`XDG_DATA_HOME` isolation.

## Next Step
- Update `progress.md`, commit pre-preflight checkpoint, and spawn a subagent to run `/niko-preflight`.
