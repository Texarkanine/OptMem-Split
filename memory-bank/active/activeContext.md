# Active Context

## Current Task: slobac-branch-remediation
**Phase:** QA - COMPLETE (FAIL)

## What Was Done
- Modified `/home/mobaxterm/git/OptMem-Split/memo`:
  - `config(d)` now resets all `KNOBS` globals to shipped defaults before applying `overrides(d)` (fixing a real bug where global-store overrides leaked into project-store bare `wake`).
  - `main(argv=None)` now accepts an optional `argv` list and resets `ME`, `SCOPE_GLOBAL`, and `KNOBS` defaults at entry.
- Modified `/home/mobaxterm/git/OptMem-Split/test.py`:
  - Removed `DEFAULTS` and all direct `cli.ME`/`cli.SCOPE_GLOBAL`/`sys.argv` mutation from `run()` (finding #9) and removed the direct `cli.SCOPE_GLOBAL` mutation block at former lines 814–823 (finding #14), replacing it with CLI-surface coverage for unset `MEMORY_DIR` (`$HOME/.optmem/memory`) in `test_store_routing`.
  - Changed `check_printed_commands` `except ValueError` from silent `continue` to explicit `check(False, ...)` failure (finding #8).
  - Stripped all `FR-*`/`NFR-*`/`C-*`/`fr1`/`fr3`/`fr6`/`fr8`/`c3` fossils across setup comments, helpers, docstrings, temp prefixes, fixture URLs, and failure messages (findings #5, #15, #18, #19, #21, #22) and regrouped branch-added tests into 4 capability sections (finding #13): `test_scope_flag_policy`, `test_exact_flag_tokens`, `test_store_routing`, `test_wake_and_printed_commands`, `test_cli_help`.
  - Fixed `# ---- scope:` header to remove `, and help` (finding #12).
  - Tightened missing-scope vs. dual-scope error oracles (`Scope is required` vs. `Choose one scope, not both`, finding #16), `nap`/`forget`/`config` store-isolation assertions (`TREE/2` and parsed active `config` + `memo config` stdout, finding #17), and `wake --here` rejection oracle (`does not take --here` + `<memo> wake` / `<memo> wake --global`, finding #20).
  - Added TDD tests for global-to-project config non-leakage in bare `wake` and in-process `cli.main(argv)` re-entrancy.
- Filed GitHub issue https://github.com/Texarkanine/OptMem-Split/issues/8 tracking findings #1 (`monolithic-test-file`) and #3 (`wrong-level`).
- Verified docs (`README.md`, `WINDOWS.md`, `memory-bank/*.md`) remain accurate with no changes needed.
- Verified full suite (`python3 test.py`: 115,709 passed, 0 failed) and `py_compile`.
- Deviations from plan: none (folded the new bare-`wake` config-isolation and `cli.main(argv)` re-entrancy checks directly into `test_store_routing` during Step 2's capability regrouping).

## Next Step
- Commit code changes and memory bank (`chore: saving work before qa phase`), then spawn QA subagent (`/niko-qa`).
