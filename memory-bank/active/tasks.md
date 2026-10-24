# Current Task: path-slug-symlinks

**Complexity:** Level 1

## Fix

`path_slug` keyed a directory with `os.path.abspath`. That cleans `.` and `..` and leaves symbolic links in the key, so one directory reached by two spellings became two memories. A chain (`link` → `mid` → the directory) slugged to the link name.

`path_slug` now calls `path.realpath` before the drive is split and the parts are joined under `path/`. On Windows, `ntpath.realpath` resolves symlinks and junctions. Off Windows, `ntpath.realpath` is `abspath`, so the junction case is tested with a path object whose `realpath` follows one junction.

Files: `memo`, `test.py`.

## QA

**Result:** PASS

- **KISS.** Production change is `path.abspath` to `path.realpath` before the drive is split. Does not block.
- **DRY.** `_JunctionPaths` rebinds `ntpath` so one `realpath` can differ. Same `path=` seam as the other Windows checks. Does not block.
- **YAGNI.** `_JunctionPaths.abspath` is unused. It does not affect the slug. Does not block.
- **Completeness.** Symlink chain, a link that is not the last component, and a junction spelling are tested. `repo_slug` is unchanged. `scope_dir` still passes the checkout root or cwd into `path_slug`. Does not block.
- **Regression.** Drive-letter shaping is the same code as before. `pretty` still keeps symlinks. Does not block.
- **Integrity.** No placeholders or debug leftovers. Does not block.
- **Documentation.** The `path_slug` docstring records the resolve-then-split order. `systemPatterns.md` is still true. Does not block.
- **Advisory.** Existing path-local memories keyed by an unresolved symlink spelling are not moved. The brief does not ask for a migration. Does not block.
