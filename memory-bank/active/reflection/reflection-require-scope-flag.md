---
task_id: require-scope-flag
date: 2026-11-19
complexity_level: 2
---

# Reflection: require-scope-flag

## Summary

Implemented [Texarkanine/OptMem-Split#5](https://github.com/Texarkanine/OptMem-Split/issues/5): single-store `memo` commands now require `--here` or `--global`, `MEMORY_DIR` moves only the global store while `--here` always targets `XDG_DATA_HOME`, printed commands carry runnable scopes (keeping project `wake` invocations bare), `-h`/`--help`/`help` exit before `store()`, `test.py` isolates `HOME`/`XDG_DATA_HOME` upfront and passes all 115,640 assertions, and all doc surfaces match. QA passed on the first run.

## Requirements vs Outcome

Every requirement (FR-1 through FR-11, NFR-1 through NFR-7, C-1 through C-5) and all 17 acceptance criteria were delivered in full, with the breaking change committed as `feat(scope)!:` (`90b214a`) carrying both required release notes. Three minor non-blocking advisories from Preflight were folded into Build (automatic FR-6 command verification in `test.py`, restoring `XDG_DATA_HOME` after `shutil.rmtree(xdg)`, and aligning secondary stale phrasing in `README.md`, `productContext.md`, and `techContext.md`).

## Plan Accuracy

The two-unit Level 2 plan (executable TDD unit followed by prose/docs unit) executed in order without backtracking. Auditing every `ME` interpolation during Plan surfaced the non-obvious `cmd_zoom()` past-end `wake` line and `cmd_init` `write_config()` hint before writing a line of code. The only minor surprises during Build were test-assertion details in two brand-new tests (trailing nap prompt after `You are awake.`, `Not awake yet. Run: ` prefix on pagination lines, and rebuilding `2-3` after `forget 0-1`), all caught immediately by running `python3 test.py`.

## Build & QA Observations

Build went cleanly from red to green; wiring `check_printed_commands()` into `test.py`'s `run()` and `sub()` helpers verified FR-6 across every command-printing path in the suite at near-zero cost. QA passed with two minor non-blocking advisories (`scope`/`store=False` convenience parameters in `test.py`'s `run()` unused by callers since new tests used `sub()`, and an internal comment above `TEMPLATE.format` in `cmd_init`).

## Insights

### Technical
- In a single-file CLI with a global `ME` prefix, commands that accept a scope flag (`note`, `nap`, `forget`, etc.) and commands that forbid one (`wake --here`) cannot share a single command-prefix variable; keeping `wake_cmd()` separate from `ME` prevents illegal printed commands across `cmd_wake()` and `cmd_zoom()`.
- `store()`'s missing-directory guard must key strictly on `SCOPE_GLOBAL`, not `os.environ.get("MEMORY_DIR")`, once `MEMORY_DIR` scopes only the global store — otherwise setting `MEMORY_DIR` silently breaks auto-creation of new project stores.
- Routing `test.py`'s in-process `run()` helper through `cli.main()` and isolating `HOME`/`XDG_DATA_HOME` before `SourceFileLoader` loads `memo` closes a real risk of tests silently mutating the operator's live stores.

### Process
- Auditing every call site of a shared global (`ME`, `MEMORY_DIR`, `SCOPE_GLOBAL`) during Plan and adding an invariant oracle (`check_printed_commands()`) inside the test harness caught edge cases before QA and produced a clean first-pass QA PASS.

### Million-Dollar Question

If explicit scoping and global-only `MEMORY_DIR` had been foundational from the start, `memo` would represent the resolved target as a small immutable scope object (path, is_global, command prefix, wake prefix) passed into command handlers instead of mutating module globals (`ME`, `SCOPE_GLOBAL`, and `KNOBS` globals in `config()`). That would also eliminate `try`/`finally` global save/restore in `wake_both()` and prevent global `config` overrides from persisting into the project half of `wake_both()`. For this fork, keeping the existing module-global structure was the right trade-off to honor NFR-2 (minimal diff from upstream OptMem).
