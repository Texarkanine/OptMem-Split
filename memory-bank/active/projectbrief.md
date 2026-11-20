# Project Brief

## User Story

As a maintainer of `OptMem-Split`, I want the tests and helpers added or modified on branch `txrk9.multi-store-filing` to be clean of the smells identified in `.slobac/2026-11-19T14-27-58/audit.md` and the monolithic/mixed-level `test.py` refactor tracked as a GitHub issue, so this branch adds clean tests without mixing in unrelated pre-existing test cleanup.

## Use-Case(s)

### Use-Case 1: Track monolithic and mixed-level test split

File a GitHub issue on `Texarkanine/OptMem-Split` capturing audit findings #1 (`monolithic-test-file`) and #3 (`wrong-level`) so splitting `test.py` into level- and domain-shaped modules is tracked separately from PR #7.

### Use-Case 2: Remediate branch-touched test and helper smells

Fix the SLOBAC audit findings in `test.py` (and the small `memo` entry-point/config reset needed to remove `run()`'s global-state coupling) for tests and helpers introduced or modified on `txrk9.multi-store-filing` vs `main.split`, while leaving pre-existing untouched tests alone.

## Requirements

1. File a GitHub issue on `Texarkanine/OptMem-Split` for audit findings #1 (`monolithic-test-file`) and #3 (`wrong-level`).
2. Strip spec requirement/constraint IDs (`FR-*`, `NFR-*`, `C-*`, `fr1`/`fr3`/`fr6`/`fr8`/`c3`) from comments, docstrings, temp-dir prefixes, fixture remote URLs, and failure messages in `test.py` (findings #5, #15, #18, #19, #21, #22).
3. Regroup the branch-added tests under capability-shaped sections and names rather than spec-checklist groupings (finding #13).
4. Make `check_printed_commands` fail explicitly on `shlex.split` `ValueError` instead of silently skipping the line (finding #8).
5. Remove `run()`'s direct mutation of `cli.ME`, `cli.SCOPE_GLOBAL`, `sys.argv`, and `DEFAULTS` globals by giving `memo`'s `main(argv=None)` and `config(d)` clean entry-point and knob-default resets (finding #9).
6. Remove `, and help` from the `# ---- scope:` section header at line 709 (finding #12).
7. Remove the direct `cli.SCOPE_GLOBAL` mutation assertions at lines 814–823 and cover default `~/.optmem/memory` global-store resolution through the public CLI surface (finding #14).
8. Assert distinct missing-scope (`Scope is required`) vs. dual-scope (`Choose one scope, not both`) diagnostics in scope-flag enforcement tests (finding #16).
9. Strengthen `nap`, `forget`, and `config` isolation assertions in scope-flag enforcement tests to verify active config entries and `TREE/2` state across both stores (finding #17).
10. Assert the specific `wake` `--here` rejection message (`does not take --here` and `wake --global` guidance) instead of `rw.stderr.strip()` (finding #20).

## Constraints

1. Do not modify pre-existing untouched tests or address pre-existing-only audit findings (#2 `shared-state`, #4 `naming-lies`, #6 `rotten-green`, #7 `tautology-theatre`, #10 `mystery-guest`, #11 `mystery-guest`).
2. Do not split `test.py` on this branch (tracked in the GitHub issue instead).
3. Preserve full test coverage and passing status of `python3 test.py` with zero regressions.
4. Follow TDD for executable behavior changes in `memo`.

## Acceptance Criteria

1. A GitHub issue exists on `Texarkanine/OptMem-Split` documenting the `monolithic-test-file` and `wrong-level` split for `test.py`.
2. Zero `FR-*`, `NFR-*`, `C-*`, `fr1`/`fr3`/`fr6`/`fr8`/`c3` deliverable fossils remain in `test.py`.
3. `test.py` never mutates `cli.SCOPE_GLOBAL`, `cli.ME`, or `DEFAULTS` globals directly.
4. `check_printed_commands` explicitly fails on unparseable shell quoting.
5. Distinct error diagnostics, active config values, `TREE/2` isolation, and unset-`MEMORY_DIR` default global-store routing are verified via the public CLI surface.
6. `python3 test.py` passes completely.

## Rework

Address [PR #7 comment #7021229465](https://github.com/Texarkanine/OptMem-Split/pull/7#issuecomment-7021229465) and eliminate non-value-adding work in the branch-added tests on `txrk9.multi-store-filing`, then push and keep PR #7's title/body accurate:

1. Remove the 5 dead cleanup calls in `test_wake_and_printed_commands` (`forget`/`nap`/`config` after blank-summary check whose store is never read again).
2. Remove the 15 subprocess calls used only to seed the in-process `cli.main(argv)` re-entrancy test in `test_store_routing` (seed in-process via `run()`).
3. Stop running `check_printed_commands()` across every iteration of the 1,994-nap synthetic-life loop (eliminating ~3,988 identical non-independent checks) while preserving printed-command validation across all distinct printing sites exercised by the branch-added tests and non-bulk checks.
4. Trim redundant flag-permutation loops (`init`, missing `MEMORY_DIR`, `wake --here`, `note` placement, `test_cli_help`) and extract a small shared git-repo/env fixture helper so the 5 branch-added functions do not repeat setup boilerplate.
5. Run pure argv/routing/help/token tests in-process via `cli.main(argv)` with `cwd`/`env` isolation, reserving real subprocesses for checks that genuinely need one (minimal-`PATH` printed-command execution, shebang/CLI smoke).
6. Push `txrk9.multi-store-filing` and update [PR #7](https://github.com/Texarkanine/OptMem-Split/pull/7)'s body (and title if needed) to accurately reflect the current diff, test count, and fixes (including the `memo.config()`/`memo.main(argv)` reset and [issue #8](https://github.com/Texarkanine/OptMem-Split/issues/8)).

