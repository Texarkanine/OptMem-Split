# Active Context

## Current Task: slobac-branch-remediation (rework)
**Phase:** QA - COMPLETE (PASS)

## What Was Done
- Modified `/home/mobaxterm/git/OptMem-Split/test.py`:
  - Deduplicated `check_printed_commands()` via `SEEN_CMD_SHAPES` (keyed by `(exe, re.sub(r"\d+", "N", segment))`), reducing ~6,350 repeated checks to 16 unique verified command shapes while preserving explicit failure on malformed shell quotes and invalid scope flags.
  - Added unified in-process `invoke(args, env=None, cwd=None)` (saving/restoring `cwd`, `HOME`, `XDG_DATA_HOME`, `MEMORY_DIR`, and validating printed commands before restoring `HOME`), rewrote `run()` to delegate to `invoke()`, removed now-unused `sub()`, and added shared `make_repo(path, origin)`.
  - Switched pure argv/routing/help/token checks in all 5 branch-added functions (`test_scope_flag_policy`, `test_exact_flag_tokens`, `test_store_routing`, `test_wake_and_printed_commands`, `test_cli_help`) onto `invoke()` while keeping the 5 minimal-`PATH` `shell=True` executions of printed `Run:` orders.
  - Removed the 5 dead cleanup calls after `bw_blank` in `test_wake_and_printed_commands`.
  - Seeded `s1`/`s2` in-process via `run()` in `test_store_routing` (removing 15 subprocess spawns).
  - Trimmed redundant flag-permutation loops (`init` 5→3, missing `MEMORY_DIR` 3→2, `bad_wake` 4→2, `note --global` placement 3→2 with end `--global` covered by `nap`/`zoom`/`import`, `test_cli_help` fresh 8→5 and live 6→3 including `["--here", "help"]` for the post-scope-strip `help` branch).
- Modified `/home/mobaxterm/git/OptMem-Split/memory-bank/techContext.md`: updated `run()`/`sub()` mention to `run()`/`invoke()` with per-shape deduplication note.
- Verified `python3 -m py_compile memo test.py relink-path-stores`, `python3 test.py` (`109362 passed, 0 failed`), and measured branch-added 5 functions dropping from `8.96s` / `146` `memo` subprocesses to `0.86s` / `0` direct `memo` subprocesses (`>10x` faster).
- Deviations from plan: incorporated Preflight Advisories 1–4 (`["--here", "help"]` in live-store help loop, accurate `--global` placement comment, `check_printed_commands()` inside `invoke()` before `HOME` restore, and Unit 3 push + PR #7 edit deferred until after QA PASS).

## Next Step
- Commit code changes and memory bank (`chore: saving work before qa phase`), run QA subagent (`/niko-qa`), then on QA PASS push branch and update PR #7 before finishing Reflect.
