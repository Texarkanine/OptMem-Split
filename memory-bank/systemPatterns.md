# System Patterns

## How This System Works

The product is one Python file (`memo`) plus an installer that drops it at `~/.optmem/memo`. Every command that the tool prints names itself (`pretty(__file__)`) so those commands still run when nothing is on PATH.

There are two kinds of store. The global one lives at `~/.optmem/memory` and is created only by `memo init`. Project stores live under `$XDG_DATA_HOME/optmem` (default `~/.local/share/optmem`), keyed by the git origin reduced to `owner/repo`, falling back to the checkout or cwd path. `$MEMORY_DIR` overrides both and skips scoping.

A named store (`MEMORY_DIR` or `--global`) that does not exist is an error. A project store is created on first write: its name is read off the repo, so there is no typo to guard. Violating that split silently opens a second identity.

Records are fixed width. Position is identity. `LOG.txt` and `TREE/` are append-only / rebuildable; never edit them by hand. Parallel sessions serialize on a `.lock` file.

## Prompt prints runnable commands

Every `Run:` line is an order the agent must be able to execute as printed. The tool path in those lines is `ME`, not the word `memo`.

## Origin is the project identity

HTTPS, SSH, and host aliases for the same `owner/repo` must resolve to one directory. An empty or missing remote is a different identity (path fallback), not a global store. Resolve the path before encoding that fallback as relative parts under `path/` (`path_slug`). On Linux and macOS, `getcwd` and the git toplevel are already physical, so the key does not change. On Windows the current directory can still name a symlink, a junction, or a substituted drive, and that spelling can leave a store behind. Never `join` an absolute filesystem path as a component, or Windows drive letters throw the store out of `optmem`. Memo does not move an old store. The repository script `relink-path-stores` lists path-local stores whose path resolves somewhere else, and moves a store only with `--move`. The installer does not copy it onto a user machine. The script leaves a store in place when the resolved directory is missing or the destination already exists.
