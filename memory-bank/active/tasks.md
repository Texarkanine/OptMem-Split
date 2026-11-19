# Task: require-scope-flag

* Task ID: require-scope-flag
* Complexity: Level 2
* Type: Simple Enhancement (breaking CLI change)

Implement [Texarkanine/OptMem-Split#5](https://github.com/Texarkanine/OptMem-Split/issues/5): require explicit `--here` or `--global` scope on single-store commands (`note`, `nap`, `recall`, `zoom`, `forget`, `config`, `import`), limit `MEMORY_DIR` to the global store so `--here` always uses `XDG_DATA_HOME` and bare `wake` reads both memories, carry scope flags on printed runnable commands (except bare `wake`), add `-h`/`--help`/`help` before any store access, isolate `test.py` upfront, and update all text and documentation surfaces.

## Test Plan (TDD)

### Behaviors to Verify

- **Scope required on all single-store commands (FR-1)**: `memo <cmd> ...` without `--here` or `--global` for each of `note`, `nap`, `recall`, `zoom`, `forget`, `config`, `import` → exits `1`, prints self-explaining scope error to stderr, leaves existing `LOG.txt` unchanged, and creates no store directory in a fresh project.
- **Conflicting scope flags rejected (FR-1)**: `memo <cmd> --here --global ...` for each of `note`, `nap`, `recall`, `zoom`, `forget`, `config`, `import` → exits `1`, prints error to stderr, writes nothing, and creates no store directory in a fresh project.
- **Valid `--here` and `--global` placement (FR-1, FR-5)**: passing `--here` or `--global` before the command, after the command, or at the end of argv on `note`, `nap`, `recall`, `zoom`, `forget`, `config`, `import` → exits `0` and targets only the requested store (`XDG_DATA_HOME/optmem/...` for `--here`, `MEMORY_DIR` or `~/.optmem/memory` for `--global`).
- **Exact flag token matching (C-3)**: `memo note --here --helpiferous`, `memo note --here help`, `memo note --here -help`, `memo note --here --globally` → exits `0` and records the literal token as memory text rather than treating it as a flag or help request.
- **`init` scope handling (FR-2, FR-3)**: `memo init`, `memo init --here`, `memo --here init`, `memo init --global`, `memo --global init` → exits `0`, always creates/reuses the global store (at `MEMORY_DIR` if set, else `~/.optmem/memory`), never creates a project store, and writes a global `config` header whose edit hint includes `--global`.
- **`MEMORY_DIR` scopes only global memory (FR-3)**: with `MEMORY_DIR` set to an initialized store and `XDG_DATA_HOME` set to a temp dir: `--global` commands read/write `MEMORY_DIR`, `--here` commands read/write under `XDG_DATA_HOME/optmem`, and bare `memo wake` prints both memories (global first from `MEMORY_DIR`, then project from `XDG_DATA_HOME`).
- **Missing global memory never auto-created (FR-3, C-1, C-2)**: with `MEMORY_DIR` set to a nonexistent path: `--global` commands (`wake --global`, `note --global "x"`, `recall --global x`) exit `1` with `"No memory at"` and `"--global init"` in stderr and do not create the directory; bare `memo wake` does not create `MEMORY_DIR`, prints `"No global memory yet"`, and wakes the project store; `memo note --here "x"` creates the project store under `XDG_DATA_HOME` and succeeds without creating `MEMORY_DIR`.
- **`wake` scope rules and paging line (FR-2, FR-6)**: `memo --here wake` and `memo wake --here` and `memo --here --global wake` → exit `1`, print usage error to stderr, create/modify nothing; `memo wake --global` reads only global memory and paginates with `Run: <memo> --global wake <k> <T>`; bare `memo wake` reads both memories and paginates the project half with `Run: <memo> wake <k> <T>` (no `--here`).
- **Printed commands carry runnable scope (FR-6)**:
  - Bare `wake` project half prints `<memo> --here note "<one line>"` when empty, `<memo> --here nap ...` for pending compressions (both blocking refusal and trailing prompt), `<memo> wake again` on blocking refusal, `<memo> --here forget ...` on blank summary, and `<memo> wake <k> <T>` on pagination; every printed `Run:` command executes successfully with `PATH=/usr/bin:/bin`.
  - Bare `wake` global half and `wake --global` print `--global` on every `note`, `nap`, `forget`, and `wake` command, and every printed `Run:` command executes successfully.
  - `memo zoom --here <past-end>` prints `Run: <memo> wake` (no `--here`); `memo zoom --global <past-end>` prints `Run: <memo> --global wake`.
  - `memo note --here` / `memo note --global` nap prompts, `memo nap`, `memo forget`, `memo import`, and `memo config` printed commands carry `--here` or `--global` and run as printed.
- **Help before `store()` (FR-8, NFR-3)**: `memo -h`, `memo --help`, `memo help`, `memo note --help`, `memo note --here -h`, `memo --here --global --help` → exit `0`, print module usage to stdout (stderr empty), leave existing stores byte-identical, and create no store directory in a fresh project (even with `MEMORY_DIR` pointing at a missing path).
- **Test isolation (NFR-5)**: `test.py` sets `HOME` and `XDG_DATA_HOME` to temporary directories and clears `MEMORY_DIR` before loading/running any command, leaving real user stores untouched.
- **Existing invariants preserved (NFR-6, NFR-7)**: block math, 2000-memory synthetic life, pagination caps, UTF-8 handling, concurrency locking, torn-write recovery, blank/corrupt summary handling, `config` knobs, Windows `ntpath` `path_slug`/`repo_slug`, and `relink-path-stores` all continue to pass.

### Test Infrastructure

- Framework: standalone Python 3 assertion script (`check(cond, msg)`), stdlib only, run with `python3 test.py` from repo root.
- Test location: `/home/mobaxterm/git/OptMem-Split/test.py`
- Conventions: in-process `run(...)` helper for fast synthetic-life assertions + `subprocess.run` / `subprocess.Popen` for CLI entry point, env isolation, PATH-less execution, and cross-process locking; temporary directories cleaned up at exit.
- New test files: none (all tests belong in `test.py`).

## Implementation Plan

### 1. Test isolation and CLI scope/help/MEMORY_DIR behavior — executable

- Files: `test.py`, `memo`

1. **Stub tests**:
   - In `test.py`, move temp `HOME` / `XDG_DATA_HOME` isolation (and `MEMORY_DIR` pop + `atexit` cleanup) to the top before loading `memo` or running any command (NFR-5).
   - Add stub test helper functions in `test.py` with docstrings describing the new test blocks (with `pass` bodies): `test_scope_flag_enforcement()`, `test_memory_dir_global_only()`, `test_wake_and_printed_commands()`, `test_help_flags()`, and `test_exact_flag_tokens()`.
   - Update existing `test.py` `run()` helper to route through `cli.main()` (with `scope="--global"` default for the single-store synthetic-life tests), update `nap_id()` / `offered()` regexes for scoped commands, and update existing subprocess invocations in `test.py` to pass `--global` or `--here` as appropriate under FR-1/FR-3.
2. **Stub interface**:
   - In `memo`, add stubbed helper functions `global_dir()` and `wake_cmd()` with docstrings and placeholder bodies (`raise NotImplementedError`), and declare `SCOPE_HERE = False` (or keep scope handling local to `main()` — only `global_dir()` and `wake_cmd()` are new module-level functions).
3. **Write tests and run red**:
   - Implement the assertions in `test_scope_flag_enforcement()`, `test_memory_dir_global_only()`, `test_wake_and_printed_commands()`, `test_help_flags()`, and `test_exact_flag_tokens()` covering every acceptance criterion (FR-1, FR-2, FR-3, FR-5, FR-6, FR-8, NFR-3, NFR-5, C-1, C-2, C-3), plus update the existing unit check at line 743 to assert `cli.memory_dir() == cli.scope_dir()` when `SCOPE_GLOBAL` is `False` even with `MEMORY_DIR` set.
   - Run `python3 test.py` and confirm the new/updated tests fail as expected (red).
4. **Write code and run green**:
   - In `memo`:
     - Implement `global_dir()` returning `os.path.expanduser(os.environ.get("MEMORY_DIR") or GLOBAL)`.
     - Update `memory_dir()` to return `global_dir() if SCOPE_GLOBAL else scope_dir()`.
     - Implement `wake_cmd()` returning `pretty(__file__) + (" --global" if SCOPE_GLOBAL else "")`.
     - Update `store()` so missing-store refusal checks `if SCOPE_GLOBAL:` (not `os.environ.get("MEMORY_DIR") or SCOPE_GLOBAL`), preserving C-1 for global stores (including `MEMORY_DIR`) and C-2 for project stores.
     - Update `cmd_wake()` and `cmd_zoom()` so `wake` invocations (`usage: %s wake`, `Run: %s wake`, `then run %s wake again`, `Not awake yet. Run: %s wake %d %d`) use `wake_cmd()`, while `note`, `nap`, `forget` hints continue using `ME`.
     - Update `wake_both()` to use `global_dir()`, run the global half with `SCOPE_GLOBAL = True` and `ME = base + " --global"`, and run the project half with `SCOPE_GLOBAL = False` and `ME = base + " --here"`, restoring `SCOPE_GLOBAL` and `ME` cleanly via `try`/`finally`.
     - Update `main()` argv parsing:
       1. Check `-h` or `--help` in `sys.argv[1:]` first -> print usage to stdout, `sys.exit(0)` (before `store()`).
       2. Extract exact `--here` and `--global` tokens from `sys.argv[1:]`.
       3. If `not argv` or `argv[0] == "help"` -> print usage to stdout, `sys.exit(0)`.
       4. Validate `cmd in COMMANDS`; otherwise print `"No such command: %s\n"` and usage to stderr, `sys.exit(1)`.
       5. For `cmd == "init"`: set `SCOPE_GLOBAL = True`, `ME = pretty(__file__) + " --global"`, call `cmd_init(global_dir(), argv[1:])`, return.
       6. For `cmd == "wake"`: if `has_here`: `die(...)` (reject `--here` and `--here --global`); if `not has_global`: call `wake_both(argv[1:])`, return; else set `SCOPE_GLOBAL = True`, `ME = pretty(__file__) + " --global"`.
       7. For the 7 scoped commands (`note`, `nap`, `recall`, `zoom`, `forget`, `config`, `import`): if `has_here == has_global`: `die(...)` with self-explaining message (`Scope is required` vs `Choose one scope, not both`); else set `SCOPE_GLOBAL = has_global`, `ME = pretty(__file__) + (" --global" if SCOPE_GLOBAL else " --here")`.
       8. Run `d = store()`, `config(d)`, `COMMANDS[cmd](d, argv[1:])`.
   - Run `python3 test.py` and verify 100% pass (0 failed).

### 2. Align module docstring, setup block, and documentation — prose/policy

- Files: `memo` (`__doc__` and `TEMPLATE`), `README.md`, `WINDOWS.md`, `memory-bank/systemPatterns.md`, `memory-bank/productContext.md`
- No tests: prose/policy artifact (note: existing `test.py` already runs `memo init` and checks `## Memory` appears; do not add brittle prose-wording change-detector tests)

1. Update `memo`'s module docstring (`__doc__`) to document `--here`/`--global` on store commands, `wake [--global]`, `help`/`-h`/`--help`, and `$MEMORY_DIR` moving only the global memory.
2. Update `memo`'s `TEMPLATE` setup block per FR-9 and FR-10: add `"Do not pipe it through head, tail, or a pager."` under startup, rewrite "While working" with `note --here` and `note --global`, and rewrite `recall`/`zoom` to show both `--here` and `--global`.
3. Update `README.md` per FR-11: replace `"Project first; --global for the rest"`, `"Put --global before any command…"`, `"Set $MEMORY_DIR to pin a single store and skip scoping"`, update the Commands table, `memo config` examples, and sync the pasted `## Memory` prompt block with `TEMPLATE`.
4. Update `WINDOWS.md` per FR-11: set `MEMORY_DIR` before `init` and use `--global` / `--here` in the Windows test commands.
5. Surgically update `memory-bank/systemPatterns.md` (FR-11) and the single invalidated bullet in `memory-bank/productContext.md` to reflect that `$MEMORY_DIR` moves only the global store, single-store commands require `--here` or `--global`, and `wake` never takes `--here`.
6. Re-run `python3 test.py` and spot-check `python3 memo --help` and `python3 memo init` (in a temp `HOME`) to verify rendered output.

## Technology Validation

No new technology - validation not required. `memo` remains a single Python 3 file using only the standard library (NFR-1).

## Dependencies

- Python 3 runtime and `git` (already present in the environment).
- No external packages or build tools.

## Challenges & Mitigations

- **Challenge 1 — `wake` paging/recovery lines leaking `--here`:** `cmd_wake()` and `cmd_zoom()` emit `Run: ... wake` lines that must carry `--global` for global scope but MUST stay bare `<memo> wake` for project scope (since `memo --here wake` is an error under FR-6), while `note`/`nap`/`forget` hints in the same functions must carry `--here`.
  - *Mitigation:* Separate `wake_cmd()` (bare for project, `--global` for global) from `ME` (`--here` for project, `--global` for global), and audit every `ME` interpolation in `memo`.
- **Challenge 2 — `cmd_init` writing unscoped `config` hint:** `write_config()` embeds `ME`, so bare `memo init` or `memo --here init` would write an invalid `memo config` or `memo --here config` comment into the global store's `config` file.
  - *Mitigation:* Set `ME = pretty(__file__) + " --global"` when dispatching `cmd == "init"`, while `TEMPLATE.format(memo=pretty(__file__), ...)` continues to use unscoped `pretty(__file__)`.
- **Challenge 3 — `test.py` accidentally writing to real user stores during transition:** Today `test.py` isolates `XDG_DATA_HOME` only at line 640 and passes no scope flags to `run()` or early subprocesses; under FR-3, a `--here` call before line 640 would write to the real `~/.local/share/optmem`.
  - *Mitigation:* Set temp `HOME`, temp `XDG_DATA_HOME`, and clear `MEMORY_DIR` at the very top of `test.py` before importing `memo` or executing any command, and verify real store mtimes/contents are unchanged.
- **Challenge 4 — In-process `run()` bypassing `cli.main()`:** Previously `test.py`'s `run()` invoked `cli.store()` and `cli.COMMANDS[...]` directly, skipping `main()`'s argv parsing, scope validation, and `ME` mutation.
  - *Mitigation:* Route `run()` through `cli.main()` while restoring `sys.argv`, `MEMORY_DIR`, `cli.ME`, `cli.SCOPE_GLOBAL`, and `DEFAULTS` per call so every in-process test exercises the real CLI dispatch.

## Pre-Mortem

- **Subprocess test `shell=True` breaks when `HOME` is changed to a temp dir:** If `pretty(__file__)` folded `MEMO` to `~/...` under one `HOME` and executed under another `HOME`, `shell=True` would fail. Setting `HOME` to a temp dir outside `/home/mobaxterm` means `pretty(__file__)` stays an absolute path `/home/mobaxterm/.../memo`, which runs under any `HOME` and minimal `PATH=/usr/bin:/bin`. Already verified in analysis; we will verify explicitly in `test_wake_and_printed_commands()`.
- **Global `config` overrides bleeding into project half during `wake_both()`:** Not introduced by this change, and out of scope per NFR-2/C-5, so we avoid modifying `config()` and keep `test.py` deterministic by not coupling unrelated global `config` edits to project `wake_both()` assertions.
- **Unintended breaking change in `store()` when `MEMORY_DIR` is set for `--here`:** If `store()` kept `if os.environ.get("MEMORY_DIR") or SCOPE_GLOBAL:`, any user with `MEMORY_DIR` set would fail to auto-create a new project store on first `note --here`. Mitigation: check `if SCOPE_GLOBAL:` only, and add a dedicated test for `note --here` in a fresh repo while `MEMORY_DIR` points at a missing directory.
- **Commit/PR missing C-4 breaking-change notes:** If the build commit is written as a plain `feat:` without `!` and the two required release notes, C-4 fails. Mitigation: make the implementation commit `feat!:` with both breaking-change notes verbatim in the commit body, and check `git log` during QA.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [x] QA

## QA Results

**Verdict:** PASS

- **Scope, completeness, and integrity:** All requirements (FR-1 through FR-11, NFR-1 through NFR-7, C-1 through C-5) and all 17 acceptance criteria from [Texarkanine/OptMem-Split#5](https://github.com/Texarkanine/OptMem-Split/issues/5) are implemented cleanly in `memo`, verified by `python3 test.py` (115,640 passed, 0 failed), and released in commit `90b214a` (`feat(scope)!:`) with both C-4 breaking-change notes.
- **Advisory (YAGNI, non-blocking):** `test.py` `run(*args, store=None, scope="--global")` includes a `store is False` branch and configurable `scope` parameter that are never called with non-default values (the new scope tests all invoke `sub()`). Harmless test-helper flexibility; does not block.
- **Advisory (comment staleness, non-blocking):** The comment above `TEMPLATE.format(...)` in `memo` (`cmd_init`) still says "so the commands in it must be the unscoped ones", whereas `TEMPLATE` now embeds `--here`/`--global` per command and only needs the bare executable path (`pretty(__file__)`) rather than `ME` (`<memo> --global`). Purely an internal comment; does not block.

