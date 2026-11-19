---
task_id: slobac-branch-remediation
date: 2026-11-19
complexity_level: 2
---

# Reflection: slobac-branch-remediation

## Summary

Remediated all 14 branch-touched SLOBAC audit findings in `test.py`, added clean state resets in `memo.config()` and `memo.main(argv=None)` (fixing a real bare-`wake` config-leak bug and eliminating `run()`'s global-state coupling), and filed [Texarkanine/OptMem-Split#8](https://github.com/Texarkanine/OptMem-Split/issues/8) to track splitting the monolithic, mixed-level `test.py`. QA passed on the second pass with `115,711 passed, 0 failed`.

## Requirements vs Outcome

Every requirement in `projectbrief.md` was delivered: findings #1 and #3 are tracked in issue #8; findings #5, #8, #9, and #12–#22 are resolved in `memo` and `test.py`; and pre-existing untouched findings (#2, #4, #6, #7, #10, #11) were left untouched. No requirements were dropped; TDD for `memo`'s `config(d)` reset also caught and proved a real cross-store config leak during bare `wake`.

## Plan Accuracy

The Level 2 sequence, file list, and scope held cleanly. Preflight caught two concrete precision details before build (`write_config`'s padded `"  WAKE_LINES   = 40     # ..."` format and lockstep `"fr3"`/`"fr6"`/`"fr8"` path renames) that prevented rework. No re-leveling or plan revisions were needed.

## Build & QA Observations

Build executed cleanly through red/green TDD, but QA Pass 1 caught two real defects in the newly added re-entrancy test inside `test_store_routing`: (1) using `zoom 1048576-2097151` formatted `wake_cmd()` instead of `ME`, so it would have passed vacuously even if `ME` reset broke; and (2) nested `call_main()` duplicated `run()` verbatim while bypassing `check_printed_commands()`. Replacing `call_main` with `run("zoom", store=s2)` resolved both findings and added 2 passing checks, and QA Pass 2 passed with zero findings.

## Insights

### Technical
- `memo.config(d)` previously mutated module globals only for overridden keys, causing global-store overrides (`WAKE_LINES=2`) to bleed into the project half of bare `memo wake` (`wake_both`). Resetting `KNOBS` defaults inside `config(d)` and `main(argv=None)` fixes both `wake_both` isolation and in-process `run()` coupling in 10 lines.
- When testing that `ME` is formatted without duplicate scope flags, choose a command path that formats `ME` directly (such as `cmd_zoom`'s missing-arg `usage:` error), not a path that delegates to `wake_cmd()`.

### Process
- In a fork with an `upstream` remote, `gh` defaults to the upstream repo (`VictorTaelin/OptMem`); always pass `-R Texarkanine/OptMem-Split` explicitly when querying or filing issues on the fork.
- When remediating test smells in a new test block, verify that new test helpers don't duplicate existing suite runners (`run()`) and that every new assertion fails under the specific mutation it claims to guard.

### Million-Dollar Question

If multi-store `wake_both` and in-process test execution had been foundational from the start, `memo` would carry a small immutable per-invocation context (`me`, `scope_global`, `knobs`, `env`) rather than six mutable module globals. That would make cross-store knob leakage and post-exit global drift structurally impossible even as new knobs are added, and is worth revisiting alongside [issue #8](https://github.com/Texarkanine/OptMem-Split/issues/8) rather than expanding this PR's diff.
