# Task: slobac-branch-remediation (rework)

* Task ID: slobac-branch-remediation
* Complexity: Level 2
* Type: simple enhancement (rework)

Eliminate non-value-adding test work introduced on branch `txrk9.multi-store-filing` in `test.py` (addressing [PR #7 comment #7021229465](https://github.com/Texarkanine/OptMem-Split/pull/7#issuecomment-7021229465)): remove dead cleanup calls, deduplicate `check_printed_commands()` across repeated identical command shapes, move pure argv/routing/help/token checks onto a shared in-process `invoke()` helper (with `run()` delegating to `invoke()`), seed re-entrancy stores in-process, trim redundant flag-permutation loops, extract a shared `make_repo()` helper, push `txrk9.multi-store-filing`, and update PR #7's body/title.

## Test Plan (TDD)

### Behaviors to Verify

- **No coverage loss across all 5 branch-added capability areas**: Every behavior from the original brief (`--here`/`--global` enforcement across all 7 single-store commands, exact flag tokens, default `~/.optmem/memory` + `MEMORY_DIR` + `XDG_DATA_HOME` routing, `init` scope-flag acceptance, bare `wake` global-to-project config isolation, `cli.main(argv)` re-entrancy, `wake --here` rejection, printed-command wire format + minimal-`PATH` shell execution, and `-h`/`--help`/`help` pre-store handling) still has an active, independent assertion.
- **Deduplicated printed-command validation**: `check_printed_commands()` validates each distinct printed-command shape (digit-normalized) once instead of repeating `3,988` identical assertions in the `1,994`-nap loop, while still explicitly failing (`check(False, ...)`) on malformed shell quotes or invalid scope flags.
- **In-process `invoke()` isolation**: Running `invoke(args, env, cwd)` restores `cwd`, `HOME`, `XDG_DATA_HOME`, and `MEMORY_DIR` in a `finally` block so subsequent tests (including pre-existing `relink-path-stores`) observe zero leaked environment or working-directory state.
- **Measured speedup and subprocess reduction**: Branch-added 5 functions drop from `~9s` / `146` `memo` subprocesses to `<1.5s` / `0` direct `memo` subprocesses (keeping the `5` minimal-`PATH` `shell=True` executions of printed `Run:` orders), and total check count drops by `~3,988` non-independent duplicates with `0` failures.

### Test Infrastructure

- Framework: Existing standalone Python 3 script `test.py` (`python3 test.py`).
- Test location: `test.py` at repository root.
- Conventions: Self-contained capability functions with `tempfile.mkdtemp` + `try`/`finally` cleanup; `check(cond, msg)` assertions; zero pre-existing untouched tests modified.
- New test files: none (splitting `test.py` is tracked in [issue #8](https://github.com/Texarkanine/OptMem-Split/issues/8)).

## Implementation Plan

### 1. Deduplicate and streamline branch-added tests in `test.py` — executable

- Files: `test.py`

1. Stub tests: No new production behavior is added (`memo` is unchanged); verify baseline test pass and profile counts (`115,711` checks, `146` `memo` subprocesses across the 5 functions) before refactoring `test.py`.
2. Stub interface: Define helper signatures `invoke(args, env, cwd=None)` and `make_repo(path, origin)` in `test.py` (with `run(*args, store=None, scope="--global")` delegating to `invoke()` and removing unused `sub()`).
3. Write tests and run red: Verify via a quick standalone probe against `check_printed_commands()` that digit-normalized shape deduplication still fails explicitly on an unparseable quote and on a missing `--here`/`--global` flag on a scoped command.
4. Write code and run green:
   - Add `SEEN_CMD_SHAPES = set()` to `check_printed_commands(text)`: skip already-checked digit-normalized shapes (`re.sub(r"\d+", "N", segment)`) after validating each distinct shape once; preserve explicit `check(False, ...)` on `shlex.split` `ValueError`.
   - Implement `invoke(args, env, cwd=None)` saving/restoring `cwd`, `HOME`, `XDG_DATA_HOME`, and `MEMORY_DIR`, capturing stdout/stderr, calling `cli.main(list(args))`, and invoking `check_printed_commands` on stdout/stderr; rewrite `run()` to delegate cleanly to `invoke()`.
   - Remove now-unused `sub()` helper and add `make_repo(path, origin)` helper.
   - Update `test_scope_flag_policy`, `test_exact_flag_tokens`, `test_store_routing`, `test_wake_and_printed_commands`, and `test_cli_help` to use `make_repo()` and `invoke()` (keeping `subprocess.run(..., shell=True, env=bare_env)` for the 5 minimal-`PATH` printed-command executions in `test_wake_and_printed_commands`).
   - Delete the 5 dead cleanup calls (`forget`, 3× `nap`, `config`) after the blank-summary check in `test_wake_and_printed_commands`.
   - Seed `s1`/`s2` in-process via `run()` in `test_store_routing` (replacing 15 `sub()` calls).
   - Trim redundant permutation loops:
     - `test_scope_flag_policy`: keep all 7 commands in `cases`; keep 3 `--here` positions (`proj zero/one/two`) and 2 `--global` positions (`glob zero/one`, with middle `--global` exercised by `recall`/`config`).
     - `test_store_routing`: missing `MEMORY_DIR` `3 → 2` (`wake --global`, `note --global`); `init` flags `5 → 3` (`["init"]`, `["init", "--here"]`, `["--global", "init"]`).
     - `test_wake_and_printed_commands`: `bad_wake` `4 → 2` (`["wake", "--here"]`, `["--here", "--global", "wake"]`).
     - `test_cli_help`: fresh-repo `8 → 5` (`["-h"]`, `["--help"]`, `["help"]`, `["note", "--here", "-h"]`, `["--here", "--global", "--help"]`); live-store `6 → 3` (`["note", "--help"]`, `["note", "--global", "-h"]`, `["help"]`).
   - Run full `python3 test.py`, `python3 -m py_compile memo test.py relink-path-stores`, and verify `git diff main.split -- test.py` leaves pre-existing untouched tests unmodified.

### 2. Sync `memory-bank/techContext.md` — prose/policy

- Files: `memory-bank/techContext.md`
- No tests: prose/policy artifact

1. Update the sentence naming `run()`/`sub()` in `memory-bank/techContext.md` to `run()`/`invoke()` so it stays factually accurate after removing unused `sub()`.

### 3. Push branch and update PR #7 — prose/policy

- Files: none (git push + GitHub PR #7 metadata on `Texarkanine/OptMem-Split`)
- No tests: prose/policy artifact

1. Check `.github/workflows/` (if present) to verify pushing does not trigger expensive automation.
2. Push `txrk9.multi-store-filing` to `origin` after QA passes.
3. Update [PR #7](https://github.com/Texarkanine/OptMem-Split/pull/7) body (and title if needed) via `gh pr edit 7 -R Texarkanine/OptMem-Split` so the description, test counts, `memo.config()`/`memo.main(argv)` reset, SLOBAC/rework test cleanup, and reference to [issue #8](https://github.com/Texarkanine/OptMem-Split/issues/8) are accurate.

## Technology Validation

No new technology - validation not required.

## Dependencies

- Python 3 (`python3 test.py`)
- `git` and `gh` CLI authenticated against `Texarkanine/OptMem-Split`

## Challenges & Mitigations

- **`os.chdir(cwd)` leaking on exception or breaking relative paths**: `MEMO` and `HERE` are already resolved to absolute paths via `os.path.realpath(__file__)` at import time, and `invoke()` wraps `os.chdir(cwd)` in `try`/`finally` restoring `old_cwd`.
- **`check_printed_commands()` shape key accidentally masking a real failure**: Because `key = re.sub(r"\d+", "N", segment)` includes the full command text (executable, flags, subcommand, quotes), a broken scope flag or malformed quote produces a distinct key and still fails explicitly; only exact repeated shapes (like 1,994 identical `nap N-N` prompts) are deduplicated.
- **Pushing before QA passes**: Push and PR #7 update happen only after all edits are committed and QA passes cleanly (or during Build verification — wait: per Niko workflow, Build produces tested commits, QA verifies commits; pushing + updating PR #7 after QA PASS or at the end of Build? Better: push and update PR #7 right after QA PASS so we never push un-QA'd code, while recording the plan step explicitly!).

## Pre-Mortem

- **Pushing un-QA'd code if QA finds a defect**: Already addressed in Challenge 3 — run Build + QA first, then push and update PR #7 once QA passes (before final Reflect completion).
- **Removing `sub()` breaks a call site in `test.py` or `check_printed_commands` coverage on a subprocess path**: Mitigation: grep `test.py` for `\bsub\(` before removing it; verify `test_wake_and_printed_commands`'s 5 `shell=True` commands still execute real subprocesses with `PATH=/usr/bin:/bin`.
- **`invoke()` with `env` missing `MEMORY_DIR` vs `run()` passing `store`**: In `run(*args, store=None, scope="--global")`, when `store is False` `MEMORY_DIR` is omitted from `env`; otherwise `MEMORY_DIR` is `store or d` while `HOME` and `XDG_DATA_HOME` stay at current `os.environ` values (`TEST_HOME`/`TEST_XDG`). Pass `env` explicitly from `run()` to `invoke()` so `run()` preserves 100% identical env semantics for the pre-existing synthetic-life tests.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
