# Current Task: path-slug-symlinks

**Complexity:** Level 1

## Fix

`path_slug` keyed a directory with `os.path.abspath`. That cleans `.` and `..` and leaves symbolic links in the key, so one directory reached by two spellings became two memories. A chain (`link` → `mid` → the directory) slugged to the link name.

`path_slug` now calls `path.realpath` before the drive is split and the parts are joined under `path/`. On Windows, `ntpath.realpath` resolves symlinks and junctions. Off Windows, `ntpath.realpath` is `abspath`, so the junction case is tested with a path object whose `realpath` follows one junction.

Files: `memo`, `test.py`.
