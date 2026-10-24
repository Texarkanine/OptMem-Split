# Progress

Resolve symbolic links, including Windows junctions, before a path-local memory key is built, so one directory is one memory. Specified in [issue #3](https://github.com/Texarkanine/OptMem-Split/issues/3).

**Complexity:** Level 1

## 2026-10-24 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Confirmed intent against issue #3
    - Classified the work as a Level 1 bug fix in `path_slug`
* Decisions made
    - Level 1: one component, isolated correction, no design fork before coding
* Insights
    - `os.path.abspath` cleans `.` and `..` and leaves links in place. The issue already checked that `os.path.realpath` of a symlink matches its target.

## 2026-10-24 - BUILD - COMPLETE

* Work completed
    - Failing tests: a symlink chain, a link that is not the last component, and a Windows junction spelling
    - `path_slug` now resolves with `path.realpath` before the path is split
    - Full suite: 109127 passed, 0 failed
* Decisions made
    - Use `path.realpath` rather than a separate link walker. On Windows that call resolves junctions. Off Windows `ntpath.realpath` is `abspath`, so the junction test supplies its own `realpath`.
* Insights
    - `scope_dir` needed no change. It already passes the checkout root or `os.getcwd()` into `path_slug`.

## 2026-10-24 - QA - COMPLETE

* Work completed
    - Reviewed `path_slug` and the new tests against the brief. No implementation edits.
    - Result: PASS
    - Reconciled persistent files. `systemPatterns.md` now states that links are resolved before the path fallback is encoded.
* Decisions made
    - Nothing in the diff has to change before acceptance. Advisories stay as notes.
    - An existing path-local store keyed by an unresolved symlink spelling is not migrated. The brief does not ask for that.
* Insights
    - `path.realpath` before `splitdrive` is the whole production change. `scope_dir` already feeds it the checkout root or `os.getcwd()`.
    - Off Windows, `ntpath.realpath` is `abspath`, so the junction case is a path double.
    - Product context and tech context needed no change. The path-layer contract belongs with the existing path-fallback rule.

## 2026-10-24 - VALIDATION (native Windows) - COMPLETE

**Did the problem exist on Windows?** Yes. With a directory junction (`via-junction` → `real-proj`), a store planted under the pre-fix slug (`...\via-junction`) was invisible to the new `memo`: `recall` returned no match and `wake` reported no memories while opening the resolved-key path (`...\real-proj`). The orphaned record was still readable when opened directly at the old store path.

**Did the fix work on Windows?** Yes, together with `relink-path-stores`. After removing the empty resolved-key shell that `wake` had auto-created (see note below), dry run showed `would move`, `--move` renamed the store onto the resolved key, and `recall` / `wake` showed the planted memory again. The old junction-key directory was gone; the resolved store held one record.

**Note:** README order applies: run `relink-path-stores` before the first post-upgrade `memo` when possible. If `memo wake` runs first, it creates an empty store at the resolved key and relink refuses to move until that shell is removed (it does not replace an existing destination).

### Anonymized cmd transcript

Isolated `%TEMP%\optmem-junction-proof`, `XDG_DATA_HOME=%TEMP%\optmem-junction-proof\xdg-data`, branch `path-slug-symlinks`, `py -3` for Python.

```bat
mkdir %TEMP%\optmem-junction-proof\real-proj
mklink /J %TEMP%\optmem-junction-proof\via-junction %TEMP%\optmem-junction-proof\real-proj
cd /d %TEMP%\optmem-junction-proof\via-junction
git init -q
set XDG_DATA_HOME=%TEMP%\optmem-junction-proof\xdg-data
set REPO=<checkout>\OptMem-Split

REM Plant #0 at OLD slug (path\...\via-junction) via log_append — simulates pre-fix store

py -3 %REPO%\memo recall SECRET
No match.

py -3 %REPO%\memo wake
== Project memory: ~\...\optmem\path\...\real-proj ==
No memories yet. Record the first with: <checkout>\memo note "<one line>"
You are awake.
(orphan at old store still contained: SECRET-JUNCTION-MEMORY proof marker)

py -3 %REPO%\relink-path-stores
left in place
  ...\optmem\path\...\via-junction
  destination already has a store: ...\optmem\path\...\real-proj

rmdir /s /q %XDG_DATA_HOME%\optmem\path\...\real-proj

py -3 %REPO%\relink-path-stores
would move
  ...\optmem\path\...\via-junction
  -> ...\optmem\path\...\real-proj

py -3 %REPO%\relink-path-stores --move
moved
  ...\optmem\path\...\via-junction
  -> ...\optmem\path\...\real-proj

py -3 %REPO%\memo recall SECRET
#0 2026-10-24 SECRET-JUNCTION-MEMORY proof marker
1 match.

py -3 %REPO%\memo wake
== Project memory: ~\...\optmem\path\...\real-proj ==
#0 2026-10-24 SECRET-JUNCTION-MEMORY proof marker
You are awake.

old junction-key store: removed
resolved store records: 1
```
