# Active Context

## Current Task: require-scope-flag
**Phase:** BUILD - COMPLETE

## What Was Done
- Implemented [Texarkanine/OptMem-Split#5](https://github.com/Texarkanine/OptMem-Split/issues/5) following TDD (red -> green) with all 115,640 assertions passing (`python3 test.py`) and zero lint/compile errors.
- Files modified:
  - `/home/mobaxterm/git/OptMem-Split/memo`
  - `/home/mobaxterm/git/OptMem-Split/test.py`
  - `/home/mobaxterm/git/OptMem-Split/README.md`
  - `/home/mobaxterm/git/OptMem-Split/WINDOWS.md`
  - `/home/mobaxterm/git/OptMem-Split/memory-bank/systemPatterns.md`
  - `/home/mobaxterm/git/OptMem-Split/memory-bank/productContext.md`
  - `/home/mobaxterm/git/OptMem-Split/memory-bank/techContext.md`
- Key implementation decisions:
  - Added `global_dir()` and `wake_cmd()` in `memo`; kept `memory_dir()` choosing `global_dir()` for `--global` and `scope_dir()` for `--here` regardless of `MEMORY_DIR`.
  - Updated `store()` to reject missing directories only when `SCOPE_GLOBAL` is True, preserving C-1 for global stores (`MEMORY_DIR` or default) and C-2 for project stores.
  - Updated `main()` to handle `-h`/`--help` and `help` before `store()`, reject `--here` on `wake`, enforce `has_here ^ has_global` on `note`/`nap`/`recall`/`zoom`/`forget`/`config`/`import`, accept/ignore scope flags on `init` (setting `ME = pretty(__file__) + " --global"` so generated `config` prints a runnable `--global config` hint), and treat only exact `--here`/`--global`/`-h`/`--help` tokens as flags.
  - Wired `check_printed_commands()` into `test.py`'s `run()` and `sub()` helpers (from Preflight advisory) to enforce FR-6 across every command-printing site automatically.
- Deviations from plan:
  - Applied the Preflight advisory items: added `check_printed_commands()` in `test.py`, restored `os.environ["XDG_DATA_HOME"] = TEST_XDG` after `shutil.rmtree(xdg)`, and surgically aligned secondary stale phrases in `README.md`, `memory-bank/productContext.md`, and `memory-bank/techContext.md`.

## Next Step
- Commit changes (`feat!:` with C-4 breaking-change notes + pre-QA checkpoint) and spawn QA subagent (`Run the /niko-qa skill`).
