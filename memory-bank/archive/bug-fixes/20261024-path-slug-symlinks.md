---
task_id: path-slug-symlinks
complexity_level: 1
date: 2026-10-24
status: completed
---

# TASK ARCHIVE: path-slug-symlinks

## SUMMARY

`path_slug` now resolves the directory with `path.realpath` before the path-local key is built, so a symlink, a Windows junction, or a substituted drive shares the physical directory's memory. Old path-local stores are not moved by `memo`. `relink-path-stores` lists them and moves them only with `--move`. The installer does not copy that script. Native Windows confirmed the junction case, including the trap where the first `memo` command creates an empty store at the new key and the script refuses to replace it. Pull request: https://github.com/Texarkanine/OptMem-Split/pull/4 (`path-slug-symlinks` → `main.split`), closes issue #3.

## REQUIREMENTS

- Resolve symbolic links, including Windows junctions, before the path is split into the `path/` key.
- `path_slug` of a symlink path and `path_slug` of its target are the same. A chain of links slugs to the directory.
- `scope_dir` still passes `git rev-parse --show-toplevel`, or `os.getcwd()` when there is no checkout, into `path_slug`.
- Origin-remote identity is unchanged. Windows drive-letter shaping stays.
- One directory is one memory no matter how the working directory was spelled.

## IMPLEMENTATION

`path_slug` in `memo` calls `path.normcase(path.realpath(p))` before `splitdrive`. `repo_slug` is unchanged. `scope_dir` needed no change.

`relink-path-stores` walks `optmem/path/`, rebuilds each store's spelled path, and compares it with `path_slug` of that path. A normal run prints `would move` or `left in place` and writes nothing. `--move` renames a store onto the resolved key. It leaves a store in place when the resolved directory is missing, the destination already exists, another store claims that destination, or the destination is inside the store. `install.sh` only replaces `memo`.

`README.md` tells a Windows user to run `python relink-path-stores` from a checkout before the next `memo` command. `systemPatterns.md` records that an empty project store created by that command blocks the move.

## TESTING

QA on the `realpath` diff: PASS. KISS, DRY, YAGNI, completeness, regression, integrity, and documentation did not block. At QA time the advisory was that an old symlink-keyed store is not migrated. The relink script was added after that.

`python3 test.py`: 109153 passed, 0 failed. The four new `path_slug` checks were red first (109123 passed, 4 failed) while `path_slug` used `abspath`. Off Windows, `ntpath.realpath` is `abspath`, so the junction check uses a path object whose `realpath` follows one junction.

Native Windows, operator transcript, reviewed against this code on 2026-10-24. It checks out for the case that was run.

- Isolated `%TEMP%\optmem-junction-proof`, `XDG_DATA_HOME` under that tree, branch `path-slug-symlinks`, `py -3`. `mklink /J via-junction real-proj`, `git init` in the junction, no origin.
- A store planted at the pre-fix `via-junction` key was invisible: `recall` printed `No match.` and `wake` opened `...\real-proj` and printed `No memories yet.`
- That `wake` calls `store()`, which creates the project directory and an empty `LOG.txt`. `relink-path-stores` then printed `left in place` and `destination already has a store`. Those strings match the script.
- After that empty destination was removed, a dry run printed `would move`, `--move` printed `moved`, and `recall` / `wake` showed `#0 2026-10-24 SECRET-JUNCTION-MEMORY proof marker` and `1 match.` The junction-key directory was gone. The resolved store held one record.

Limits of that run, kept on purpose:

- The plant step is a comment in the transcript (`log_append` at the old slug), not a printed command. `git rev-parse --show-toplevel` is not shown. The printed `wake` path and the relink arrow are what show that Windows resolved the junction.
- The run used a directory junction. A symlink and a substituted drive were not exercised on Windows.
- The pasted `wake` output starts at the project section. `wake` also prints the global memory, or `No global memory yet`, before that.

## LESSONS LEARNED

- On Linux, WSL, and macOS, `getcwd` and `git rev-parse --show-toplevel` are already physical. A normal `cd` does not change the key. This split shows up when Windows `GetCurrentDirectory` still contains a symlink, junction, or subst spelling.
- `memo` does not migrate. The first command after the upgrade creates the new key. `os.path.lexists` treats that empty directory as a store, so relink will not move the old one until the empty destination is removed.
- Do not remove the old store in that situation. Remove the destination the script names, and only when it has no memories.

## PROCESS IMPROVEMENTS

Level 1 has no `/niko-archive` mapping. This run used the archive format because the operator invoked `/niko-archive`, as with `windows-split-scope`. There is no Level 1 reflection file. This archive inlines the brief, the QA note, and the Windows transcript.

## TECHNICAL IMPROVEMENTS

None. Relink stays a repository script. It must not overwrite a destination.

## NEXT STEPS

- Merge https://github.com/Texarkanine/OptMem-Split/pull/4 after the breaking-change title and the Windows upgrade note are acceptable.
- Put the Windows upgrade steps on the GitHub release. Users skip versions, so that note has to stand alone.
- A native symlink run and a subst-drive run are still open. This junction run does not cover them.
