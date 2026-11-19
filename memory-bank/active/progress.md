# Progress

Remediate SLOBAC audit findings on tests and helpers introduced or modified on branch `txrk9.multi-store-filing`, give `memo` a clean re-entrant `main(argv=None)` and `config(d)` default reset so `test.py` stops poking internal globals, and file a GitHub issue on `Texarkanine/OptMem-Split` for splitting monolithic/mixed-level `test.py`.

**Complexity:** Level 2

## 2026-11-19 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Mapped `git diff main.split...HEAD -- test.py` against all 22 findings in `.slobac/2026-11-19T14-27-58/audit.md`.
    - Confirmed scope with operator: file GitHub issue for #1 + #3; fix branch-touched findings (#5, #8, #9, #12–#22); leave pre-existing untouched tests (#2, #4, #6, #7, #10, #11) alone.
    - Classified as Level 2 (Simple Enhancement).
* Decisions made
    - Include #9 (`run()` global-state coupling) via a minimal `main(argv=None)` + `config(d)` knob reset in `memo` (which also prevents global-store config overrides from leaking into the project store during bare `wake`).
    - Fold #3 (`wrong-level`) into the `monolithic-test-file` GitHub issue on `Texarkanine/OptMem-Split` rather than splitting `test.py` on this branch.
* Insights
    - `config(d)` in `memo` currently only writes overridden knobs to module globals without restoring defaults first, so a global-store override during `wake_both` leaks into the subsequent project-store wake.
    - Removing the `cli.SCOPE_GLOBAL` mutation checks at lines 814–823 requires adding a CLI-surface test for `--global` when `MEMORY_DIR` is unset (falling back to `$HOME/.optmem/memory`), which the subprocess tests did not previously cover.
