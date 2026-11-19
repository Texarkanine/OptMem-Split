# Task: slobac-branch-remediation

* Task ID: slobac-branch-remediation
* Complexity: Level 2
* Type: simple enhancement

Remediate the SLOBAC audit findings in `.slobac/2026-11-19T14-27-58/audit.md` for tests and helpers introduced or modified on branch `txrk9.multi-store-filing` (findings #5, #8, #9, #12, #13, #14, #15, #16, #17, #18, #19, #20, #21, #22), add clean re-entrant `main(argv=None)` and `config(d)` default resets in `memo` to remove `run()`'s global-state coupling, and file a GitHub issue on `Texarkanine/OptMem-Split` tracking the monolithic/mixed-level `test.py` split (findings #1 and #3). Pre-existing untouched tests and findings (#2, #4, #6, #7, #10, #11) remain untouched.

## Test Plan (TDD)

### Behaviors to Verify

- **Global config override does not leak into project wake during bare `wake`**: Given a global store overriding `PART_LINES=2` (or `WAKE_LINES=2`) and a project store using defaults with >2 lines, running bare `memo wake` formats the project half with default `WAKE_LINES`/`PART_LINES` (not the global store's override) → project store wake prints all default-budget lines without inheriting the global override.
- **Re-entrant `cli.main(argv)` resets module state without caller mutation**: Calling `cli.main(["--global", "config", "WAKE_LINES=40"])` followed by `cli.main(["--global", "wake"])` on another store (with default config) resets `ME`, `SCOPE_GLOBAL`, and `KNOBS` defaults internally → `run()` succeeds across all synthetic-life checks without mutating `cli.ME`, `cli.SCOPE_GLOBAL`, `DEFAULTS`, or `sys.argv`.
- **Unset `MEMORY_DIR` routes `--global` to `$HOME/.optmem/memory`**: Running `memo init` and `memo note --global` with `MEMORY_DIR` unset and `HOME` isolated writes to `$HOME/.optmem/memory/LOG.txt` and creates nothing under `$XDG_DATA_HOME` → verified via public CLI subprocess (replacing direct `cli.SCOPE_GLOBAL` mutation).
- **Distinct scope-error diagnostics**: Running any single-store command (`note`, `nap`, `recall`, `zoom`, `forget`, `config`, `import`) with no scope flag prints `"Scope is required"` (plus `--here` and `--global`); running with both `--here` and `--global` prints `"Choose one scope, not both"` (plus `--here` and `--global`).
- **Store isolation for `nap`, `forget`, and `config`**: `nap --here` writes only `proj_store/TREE/2` (leaving `g_dir/TREE/2` absent); `nap --global` writes only `g_dir/TREE/2`; `forget --here` empties `proj_store/TREE/2` while preserving `g_dir/TREE/2`; `config --here WAKE_LINES=40` writes uncommented `WAKE_LINES = 40` to `proj_store/config` (and `memo config --here` reports `40`) while `g_dir/config` stays at default `96`; `config --global WAKE_LINES=50` writes uncommented `WAKE_LINES = 50` to `g_dir/config` while `proj_store/config` remains `40`.
- **Specific `wake --here` rejection diagnostic**: Running `memo --here wake`, `memo wake --here`, `memo --here --global wake`, or `memo wake 1 --here` exits 1 with empty stdout, creates no project store, and prints `"does not take --here"` and `<memo> wake --global` to stderr.
- **Strict shell-quote parsing in `check_printed_commands`**: If `shlex.split` raises `ValueError` on a matched runtime command line, `check_printed_commands` records an explicit test failure instead of silently continuing.

### Test Infrastructure

- Framework: Custom standalone Python 3 script (`test.py`) using `check(cond, msg)` counters and both in-process `run()` and subprocess `sub()` helpers.
- Test location: `test.py` at repository root (`python3 test.py`).
- Conventions: Self-contained functions/blocks with `tempfile.mkdtemp` + `try`/`finally` cleanup for new functions; `check(...)` assertions with descriptive failure messages.
- New test files: none (splitting `test.py` is tracked in the new GitHub issue).

## Implementation Plan

### 1. Re-entrant `memo.main(argv=None)` and `memo.config(d)` knob reset — executable

- Files: `memo`, `test.py`

1. Stub tests: Add an empty test case inside the store-routing test section of `test.py` (testing global config non-leakage into project bare `wake` and unset-`MEMORY_DIR` default `~/.optmem/memory` routing) and prepare `run()` to call `cli.main(argv)` directly.
2. Stub interface: Update `def main(argv=None):` signature in `memo` (keeping body behavior unchanged initially so the new global-override-leak test fails red).
3. Write tests and run red: Implement the global-override-non-leakage test in `test.py` (set `WAKE_LINES=2` in global store, keep 4 memories in project store with default `WAKE_LINES`, run `memo wake`, assert all 4 project memories appear in bare `wake` output). Run `python3 test.py` and confirm the new test fails because `config(d)` does not reset `KNOBS` defaults.
4. Write code and run green:
   - In `memo` `config(d)`, reset every knob in `KNOBS` to its default before applying `overrides(d)`.
   - In `memo` `main(argv=None)`, reset `ME = pretty(__file__)`, `SCOPE_GLOBAL = False`, and every knob in `KNOBS` to its default, and parse `sys.argv[1:] if argv is None else list(argv)`.
   - In `test.py`, remove `DEFAULTS` (lines 48–49) and remove `cli.ME`, `cli.SCOPE_GLOBAL`, `DEFAULTS`, and `sys.argv` mutation from `run()`, calling `cli.main(([scope] if scope else []) + list(args))`.
   - Run `python3 test.py` and verify the new test and existing suite pass.

### 2. Remediate branch-touched smells in `test.py` — executable

- Files: `test.py`

1. Stub tests: Map the 5 branch-added test functions into 4 capability-shaped sections (before/after TOC below) and stub the tightened assertions for scope errors, `nap`/`forget`/`config` isolation, `wake --here` rejection, unset-`MEMORY_DIR` default global store, and strict `check_printed_commands` `ValueError` failure.
   - Before → After TOC:
     - `test_scope_flag_enforcement` (`FR-1, FR-5`) + `test_exact_flag_tokens` (`C-3`) → `# ---- scope flags and token parsing ----` (`test_scope_flag_policy`, `test_exact_flag_tokens`)
     - `test_memory_dir_global_only` (`FR-2, FR-3, C-1, C-2`) + removed lines 814–823 (`cli.SCOPE_GLOBAL`) → `# ---- store routing: MEMORY_DIR, XDG_DATA_HOME, and default global ----` (`test_store_routing`)
     - `test_wake_and_printed_commands` (`FR-2, FR-6`) → `# ---- printed command contracts and wake scope ----` (`test_wake_and_printed_commands`)
     - `test_help_flags` (`FR-8, NFR-3`) → `# ---- CLI help and usage ----` (`test_cli_help`)
2. Stub interface: No new production interface changes (helper `check_printed_commands` and test functions live in `test.py`).
3. Write tests and run red: Verify on the tightened assertions that `check_printed_commands` raises an explicit failure on unbalanced quotes (verified cleanly via a one-off probe or assertion check before running full suite) and verify all new/tightened assertions against current `memo`.
4. Write code and run green:
   - Strip `NFR-5` and `FR-6` from line 21 comment, `check_printed_commands` docstring, and `sub` docstring (finding #5).
   - Change `except ValueError: continue` in `check_printed_commands` to `check(False, "unparseable printed command: %r" % line); continue` (finding #8).
   - Update line 709 header from `# ---- scope: project slug resolution, --here/--global, MEMORY_DIR, and help` to `# ---- scope: project slug resolution and checkout routing` (finding #12).
   - Delete lines 814–823 (`cli.SCOPE_GLOBAL = True/False` direct global-mutation block) (finding #14) and ensure unset-`MEMORY_DIR` default `~/.optmem/memory` routing is covered via CLI subprocess in `test_store_routing`.
   - Strip all `FR-*`, `NFR-*`, `C-*`, `fr1`/`fr3`/`fr6`/`fr8`/`c3` fossils from docstrings, comments, temp-dir prefixes, remote URLs, and failure messages across the branch-added tests (findings #15, #18, #19, #21, #22) and regroup into the 4 capability sections above (finding #13).
   - Strengthen missing-scope vs. dual-scope assertions in `test_scope_flag_policy` to require `"Scope is required"` vs. `"Choose one scope, not both"` (finding #16).
   - Strengthen `nap`, `forget`, and `config` isolation assertions in `test_scope_flag_policy` to verify `TREE/2` existence/contents/emptiness and active uncommented `WAKE_LINES = 40` / `WAKE_LINES = 50` plus `memo config` output across both stores (finding #17).
   - Strengthen `wake --here` rejection assertions in `test_wake_and_printed_commands` to require `"does not take --here"` and `cli.pretty(MEMO) + " wake --global"` in stderr (finding #20).
   - Run full `python3 test.py` and verify 0 failures and clean diff against `main.split` (confirming untouched pre-existing tests for #2, #4, #6, #7, #10, #11 were not modified).

### 3. File GitHub issue for monolithic and mixed-level `test.py` — prose/policy

- Files: none (GitHub issue on `Texarkanine/OptMem-Split`)
- No tests: prose/policy artifact

1. Create a GitHub issue on `Texarkanine/OptMem-Split` using `gh issue create -R Texarkanine/OptMem-Split` covering audit findings #1 (`monolithic-test-file`) and #3 (`wrong-level`): summarize the current 1,448-line mixed-domain, mixed-tier layout (pure block math, in-process synthetic-life lifecycle, 16-process concurrency/recovery, git-backed CLI scope/routing/help e2e, and `relink-path-stores`) and prescribe splitting into level- and domain-shaped test modules with a shared helper module so fast and slow tiers can run independently.
2. Record the created issue URL in `memory-bank/active/progress.md`.

### 4. Documentation check — prose/policy

- Files: `memory-bank/techContext.md` (only if factually invalidated)
- No tests: prose/policy artifact

1. Review `README.md`, `WINDOWS.md`, and `memory-bank/techContext.md` to confirm nothing became inaccurate (no user-facing CLI flags or behavior changed, only bugfix on global-to-project config leak in bare `wake` and internal `main(argv=None)` signature).

## Technology Validation

No new technology - validation not required.

## Dependencies

- Python 3 (for `python3 test.py`)
- `gh` CLI authenticated against `Texarkanine/OptMem-Split` (for filing the issue)

## Challenges & Mitigations

- **`check_printed_commands` triggering `ValueError` on synthetic-life memory text**: If any existing test emits a line containing `Run: `, `usage: `, or `then run ` with an unbalanced quote inside memory text, changing `except ValueError` from silent skip to failure would expose it. Mitigation: run full `python3 test.py` immediately after updating `check_printed_commands` and inspect any line that triggers it; tighten the command-line regex only if a non-command memory line matched falsely.
- **Coverage regression when deleting lines 814–823 (`cli.SCOPE_GLOBAL` tests)**: Line 817 was the only assertion covering `--global` with `MEMORY_DIR` unset (`$HOME/.optmem/memory`). Mitigation: explicitly add CLI subprocess coverage for unset `MEMORY_DIR` in `test_store_routing` before deleting lines 814–823.
- **Accidental edits to pre-existing untouched tests**: Findings #2, #4, #6, #7, #10, #11 are out of scope. Mitigation: check `git --no-pager diff main.split...HEAD -- test.py` after edits to confirm only branch-touched regions changed.
- **Targeting wrong GitHub repo with `gh issue create`**: Earlier `gh issue list` defaulted to `upstream` (`VictorTaelin/OptMem`). Mitigation: pass `-R Texarkanine/OptMem-Split` explicitly to `gh issue create`.

## Pre-Mortem

- **Wrong repo receives the GitHub issue**: Already covered by Challenge 4 (`-R Texarkanine/OptMem-Split`).
- **`memo` `main(argv=None)` breaks an in-process caller or `test.py` `run()` assumption**: If any pre-existing test in `test.py` sets a knob or relies on `sys.argv` when calling `run()`, removing `sys.argv` mutation might change behavior. Plan response: inspect every `run(...)` call site before editing `run()`; `main(argv=None)` preserves `sys.argv[1:]` when `argv is None` so direct CLI execution is 100% unchanged.
- **Global-config-leak test in `wake_both` doesn't reproduce with `WAKE_LINES` on 4 notes**: Because `cover(4, 2)` produces 2 lines (e.g. `#0-1` + `#2-3`) only when summaries exist; without summaries, `cmd_wake` refuses or prints raw lines depending on `T` vs `WAKE_LINES`. Plan response: verify the exact reproduction setup (`note` + `nap` so `cover` actually compresses to `WAKE_LINES=2` when leaked, vs printing raw/expanded lines when default `WAKE_LINES=96` applies) when writing the red test in Step 1.3.

## QA Findings

Result: **FAIL** — Build must rerun to fix the two blocking findings below in `test.py`.

1. **Blocking (Completeness / Integrity) — Vacuous `ME` re-entrancy check in `test_store_routing` (`test.py:1228-1232`)**: `r3 = call_main(s2, ["--global", "zoom", "1048576-2097151"])` claims to verify that repeated `cli.main(argv)` calls do not duplicate `--global` in `ME`, but `cmd_zoom` for an out-of-range block (`memo:912-914`) prints `wake_cmd()` (`memo:201-203`), which recomputes `pretty(__file__) + (" --global" if SCOPE_GLOBAL else "")` and never reads `ME`. Deleting `ME = pretty(__file__)` from `memo.main()` leaves `r3` passing even when `cli.ME` accumulates repeated `--global` flags. Invoke a command path that formats `ME` (e.g., `zoom` with missing block ID `["--global", "zoom"]` -> `usage: %s zoom <lo>-<hi>`, or `note` with missing text) so the test fails if `ME` is not reset.
2. **Blocking (DRY) — Duplicate in-process runner `call_main` in `test_store_routing` (`test.py:1204-1218`)**: The nested `call_main(store_dir, argv)` helper duplicates 14 lines of the existing module-level `run(*args, store=None, scope="--global")` helper (`test.py:158-182`) verbatim while bypassing `check_printed_commands()`. Replace `call_main` with `run("wake", store=s1)`, `run("wake", store=s2)`, and `run("zoom", store=s2)` so the re-entrancy test reuses `run()` and checks printed commands.
3. **Advisory (Non-blocking) — Redundant substring check in `test_wake_and_printed_commands` (`test.py:1266`)**: `(exe + " wake") in rw.stderr` is strictly implied by `(exe + " wake --global") in rw.stderr`; checking backticked `` "`%s wake`" % exe `` would independently assert the bare-`wake` hint alongside the `--global` hint.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [ ] QA
