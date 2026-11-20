---
task_id: require-scope-flag
complexity_level: 2
date: 2026-11-19
status: completed
---

# TASK ARCHIVE: require-scope-flag

## SUMMARY

Implemented [Texarkanine/OptMem-Split#5](https://github.com/Texarkanine/OptMem-Split/issues/5) on branch `txrk9.multi-store-filing` (`90b214a`, `feat(scope)!:`). Single-store `memo` commands (`note`, `nap`, `recall`, `zoom`, `forget`, `config`, `import`) now require an explicit `--here` or `--global` flag anywhere in argv, `MEMORY_DIR` moves only the global memory while `--here` always uses `XDG_DATA_HOME/optmem` and bare `wake` reads both stores, printed commands carry runnable scopes (keeping project `wake` invocations bare), `-h`/`--help`/`help` print usage to stdout before `store()` runs, `test.py` isolates `HOME`/`XDG_DATA_HOME` upfront and passes 115,640 assertions, and all documentation surfaces match.

## REQUIREMENTS

- **FR-1 & FR-5 (Scope flag):** Require exactly one of `--here` or `--global` (anywhere in argv) on `note`, `nap`, `recall`, `zoom`, `forget`, `config`, and `import`; fail with exit code `1`, a self-explaining stderr message, and zero writes when omitted or when both are passed.
- **FR-2 (Unchanged commands):** Bare `wake` reads both memories (global first, then project); `wake --global` reads only global; `init` always creates the global memory and accepts/ignores a scope flag; `note` prints `Saved as #N.`
- **FR-3 (`MEMORY_DIR` global-only):** `MEMORY_DIR` moves only the global memory (default `~/.optmem/memory`); `--here` always targets `XDG_DATA_HOME/optmem` (default `~/.local/share/optmem`); bare `wake` reads both stores even when `MEMORY_DIR` is set.
- **FR-6 (Runnable scoped commands):** `ME` carries ` --here` or ` --global` so every printed hint, usage line, and nap prompt runs as printed, except `wake` never takes `--here` (project paging and recovery lines stay bare `<memo> wake`, and `memo --here wake` exits `1`).
- **FR-8 & NFR-3 (Help):** `-h` or `--help` anywhere in argv, or `memo help`, prints module usage to stdout and exits `0` before `store()` runs, creating nothing.
- **FR-9, FR-10, FR-11 (Text surfaces):** Align `memo` (`__doc__` and `TEMPLATE`, including `"Do not pipe it through head, tail, or a pager."`), `README.md`, `WINDOWS.md`, `memory-bank/systemPatterns.md`, and invalidated bullets in `memory-bank/productContext.md` and `memory-bank/techContext.md`.
- **C-1..C-5 & NFR-1..NFR-7:** Missing global store is always an error except `init`; project stores auto-create on first write; only exact `--here`, `--global`, `-h`, `--help` tokens are flags; keep single stdlib-only file with minimal diff from upstream; isolate `test.py` upfront; land as `feat!:` with both required breaking-change notes.

## IMPLEMENTATION

- `memo`: Added `global_dir()` and `wake_cmd()`; updated `memory_dir()` to resolve `global_dir()` for `--global` and `scope_dir()` for `--here`; updated `store()` to reject missing directories only when `SCOPE_GLOBAL` is True; updated `cmd_wake()` and `cmd_zoom()` to use `wake_cmd()` for `wake` invocations and `ME` for single-store commands; updated `wake_both()` to read `global_dir()` and wrap global (`--global`) and project (`--here`) halves with `try`/`finally`; updated `main()` to handle `-h`/`--help`/`help` before `store()`, dispatch `init` with `ME = pretty(__file__) + " --global"`, reject `--here` on `wake`, and enforce `has_here ^ has_global` on the 7 single-store commands; updated `__doc__` and `TEMPLATE`.
- `test.py`: Moved temp `HOME`/`XDG_DATA_HOME` isolation and `MEMORY_DIR` clearing to the top of the file before loading `memo`; routed `run()` through `cli.main()` and added `sub()` + `check_printed_commands()` to automatically enforce FR-6 across every command-printing site; updated existing invocations for explicit scoping and added five test suites (`test_scope_flag_enforcement`, `test_memory_dir_global_only`, `test_wake_and_printed_commands`, `test_help_flags`, `test_exact_flag_tokens`).
- `README.md`, `WINDOWS.md`, `memory-bank/systemPatterns.md`, `memory-bank/productContext.md`, `memory-bank/techContext.md`: Updated CLI syntax, `$MEMORY_DIR` behavior, setup block copy, Windows smoke snippet, and standing architecture/test contracts.

## TESTING

- TDD red-then-green execution: wrote all 5 new test suites and isolation harness first, verified expected red failure against prior `memo`, then implemented changes in `memo`.
- Full test suite: `python3 test.py` passed with `115640 passed, 0 failed` (including PATH-less `shell=True` execution of printed `Run:` orders and automatic FR-6 validation on every `run()` and `sub()` call).
- Mechanical & manual checks: `python3 -m py_compile memo test.py`, `ReadLints` (0 errors), and spot-checks of `python3 memo --help` and `python3 memo init` in a clean temp `HOME`.
- Preflight (`PASS WITH ADVISORY`) and QA (`PASS`, with two minor non-blocking advisories: unused `scope`/`store=False` flexibility in `test.py`'s `run()` helper and an internal comment above `TEMPLATE.format` in `cmd_init`) both passed on the first run.

## LESSONS LEARNED

- Commands that require a scope flag (`note`, `nap`, `forget`, etc.) and commands that reject `--here` (`wake`) cannot share a single `ME` command prefix; keeping `wake_cmd()` separate from `ME` prevents illegal printed commands across `cmd_wake()` and `cmd_zoom()`.
- Once `MEMORY_DIR` scopes only the global memory, `store()`'s missing-directory check must key strictly on `SCOPE_GLOBAL`, not `os.environ.get("MEMORY_DIR")`, or setting `MEMORY_DIR` breaks auto-creation of new project stores.
- Isolating `HOME`/`XDG_DATA_HOME` at the top of `test.py` before `SourceFileLoader` loads `memo` prevents tests from touching the operator's real stores.

## PROCESS IMPROVEMENTS

- Auditing every call site of shared module globals (`ME`, `MEMORY_DIR`, `SCOPE_GLOBAL`) during Plan and embedding a printed-command invariant checker (`check_printed_commands()`) directly in `test.py` surfaced edge cases before implementation and produced a clean first-pass QA PASS.

## TECHNICAL IMPROVEMENTS

- If explicit scoping and global-only `MEMORY_DIR` had been foundational from the start, passing a small immutable scope object (path, is_global, command prefix, wake prefix) into handlers instead of mutating module globals (`ME`, `SCOPE_GLOBAL`, and `KNOBS` globals in `config()`) would eliminate `try`/`finally` state save/restore in `wake_both()` and avoid global `config` overrides bleeding into the project half. Kept module globals here to honor NFR-2 minimal diff from upstream.

## NEXT STEPS

Open a draft pull request against `main.split` for operator review and merge.
