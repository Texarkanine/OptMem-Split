---
task_id: slobac-branch-remediation
date: 2026-11-19
complexity_level: 2
---

# Reflection: slobac-branch-remediation

## Summary

Remediated all 14 branch-touched SLOBAC audit findings in `test.py`, added clean state resets in `memo.config()` and `memo.main(argv=None)` (fixing a bare-`wake` global-to-project config leak and removing `run()`'s global-state coupling), filed [Texarkanine/OptMem-Split#8](https://github.com/Texarkanine/OptMem-Split/issues/8) to track splitting `test.py`, and followed up with a rework pass eliminating non-value-adding test overhead (`8.96s` / `146` `memo` subprocesses → `0.86s` / `0` direct `memo` subprocesses; `~6,350` duplicate command checks → `16` unique verified shapes; `109,362 passed, 0 failed`).

## Requirements vs Outcome

Every requirement in both the original brief and the rework brief (addressing [PR #7 comment #7021229465](https://github.com/Texarkanine/OptMem-Split/pull/7#issuecomment-7021229465)) was delivered: findings #1 and #3 are tracked in issue #8; findings #5, #8, #9, and #12–#22 are resolved; dead cleanup calls, redundant flag-permutation loops, duplicate `check_printed_commands()` assertions, and unnecessary `memo` subprocess spawns in the 5 branch-added functions were eliminated; pre-existing untouched tests (#2, #4, #6, #7, #10, #11) stayed untouched; and the branch is pushed with PR #7 updated.

## Plan Accuracy

Both Level 2 plans held cleanly with zero re-leveling. Preflight caught high-leverage precision details before both builds (`write_config` whitespace padding and lockstep renames on pass 1; preserving one scoped `["--here", "help"]` check for `memo:987-988` and checking printed commands inside `invoke()` before `HOME` restore on rework).

## Build & QA Observations

Pass 1 QA caught two defects in the new re-entrancy test (`zoom 1048576-2097151` printed `wake_cmd()` instead of `ME`, and nested `call_main()` duplicated `run()`), both resolved cleanly in `f1340dd`. Rework Build and QA passed on the first attempt with zero blockers (`109,362 passed, 0 failed`).

## Insights

### Technical
- `memo.config(d)` previously overwrote only overridden knobs without restoring defaults first, allowing global overrides (`WAKE_LINES=2`) to leak into the project store during bare `wake`; resetting `KNOBS` defaults in `config(d)` and `main(argv=None)` fixes both `wake_both` isolation and in-process `invoke()`/`run()` isolation in 10 lines.
- Deduplicating `check_printed_commands()` by `(exe, re.sub(r"\d+", "N", segment))` keeps passive coverage of all distinct command-printing sites across the suite (16 shapes) without inflating check counts by ~6,350 identical loop assertions.
- Driving pure argv/routing/help tests through in-process `invoke()` (keeping `subprocess.run(..., shell=True)` strictly for minimal-`PATH` execution of printed `Run:` orders) cut the 5 branch-added functions from `8.96s` to `0.86s` (>10× faster).

### Process
- A SLOBAC audit catches structural smells well, but profiling wall-clock time and subprocess counts separately caught wasted work SLOBAC didn't flag (5 dead cleanup calls, 15-subprocess seeding for an in-process test, and over-parameterized permutation loops).
- In a fork with an `upstream` remote, `gh` defaults to `upstream` (`VictorTaelin/OptMem`); always pass `-R Texarkanine/OptMem-Split` explicitly.

### Million-Dollar Question

If multi-store `wake_both` and in-process test execution had been foundational from the start, `memo` would carry a small immutable per-invocation context (`me`, `scope_global`, `knobs`, `env`) rather than six mutable module globals, and `check_printed_commands()` would scan directly for `exe` rather than five hardcoded English wrapper prefixes. Both are worth considering alongside [issue #8](https://github.com/Texarkanine/OptMem-Split/issues/8) rather than expanding PR #7.
