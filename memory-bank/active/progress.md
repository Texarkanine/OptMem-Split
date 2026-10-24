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
