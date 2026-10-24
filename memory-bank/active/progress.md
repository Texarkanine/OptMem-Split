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
