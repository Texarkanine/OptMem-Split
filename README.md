# OptMem

Permanent memory for AI agents. A 400-ish-token prompt, a script, plug and play.

This fork of [VictorTaelin/OptMem](https://github.com/VictorTaelin/OptMem) flips the default: **one memory store per project**, plus one global memory that follows you everywhere. Project first; `--global` for the rest.

![how OptMem works](anim/optmem.gif)

## Install

```sh
curl -fsSL https://raw.githubusercontent.com/Texarkanine/OptMem-Split/main.split/install.sh | sh
```

It prints a `## Memory` block. Paste that at the top of your agent's
`AGENTS.md` (or `CLAUDE.md`), and you are done. Run the same line again to
update.

The tool lands at `~/.optmem/memo`; put `~/.optmem` on `PATH` to type `memo`.

## Commands

| | |
|---|---|
| `memo wake` | read both memories — global, then project; first command of every session |
| `memo note "..."` | record one memory: one line, up to 280 bytes (project by default) |
| `memo nap` | answer the merges that came due |
| `memo recall <regex>` | search every memory ever recorded, word for word |
| `memo zoom <lo>-<hi>` | open a tree node into its two halves |
| `memo forget <lo>-<hi>` | drop a bad summary; the next nap rebuilds it |

Put `--global` before any command to reach the memory that follows you into every project.
Merges arrive one at a time, in the output of `note`. Nothing ever runs in the background.

## Why Split Memory

A single log is one identity, and wake spends its reading budget on the present.
That is right for one continuous workstream and wrong for several: 
N interleaved projects make each one's detail decay at the rate of the other N−1,
so a repo left alone for six months wakes up remembering nothing — 
its memories intact in the log and out of reach.

So every command speaks to the memory of the project in `$PWD`, 
keyed by the origin remote reduced to `owner/repo` 
(every worktree and host alias for one repo is one memory). 
`--global` reaches the one that follows you everywhere. `wake` alone reads both: 
who you are, then where you are. Almost everything belongs in the project; 
use `--global` only for what would still be true tomorrow in a repository you have never seen.

## Files

```
~/.optmem/
  memo              the tool: one file of Python 3, no dependencies
  memory/           the global memory (create with `memo init`)
    LOG.txt         every memory, one per line, append-only, never edited
    TREE/           the summaries: a cache, rebuildable from the log alone
    config          the sizes, written by `memo config`

$XDG_DATA_HOME/optmem/   (default: ~/.local/share/optmem)
  repo/<owner>/<repo>/   one memory per project, same layout as memory/
  path/<directory>/      same layout, for a directory with no origin
```

A directory with no origin remote is keyed by its path. On Linux and macOS that path is already physical after `cd`, so this does not change an existing store. On Windows the current directory can still name a symlink, a junction, or a substituted drive, and the key is now the resolved directory. A store under the old spelling stays on disk. This repository contains `relink-path-stores` for that Windows case. From a checkout, on the machine that holds the stores, run `./relink-path-stores`. It shows each store it would move. Add `--move` to move them. It does not replace a store that is already at the destination.

```sh
memo config                  # show the sizes
memo config WAKE_LINES=300   # how many lines wake prints (96 ≈ 8k tokens)
memo config WAKE_LINES=      # back to the default
```

`WAKE_LINES` is the only size worth touching, and it is a reading budget, not
a storage budget: change it whenever, in either direction, and nothing is
recomputed.

Records are fixed width, so position *is* identity and every lookup is one
seek. At a million memories (608 MB), `wake` takes 0.03s.

Set `$MEMORY_DIR` to pin a single store and skip scoping — a synced folder, a git repo.

## The prompt

This is what the installer prints, and the whole of the integration.

```markdown
## Memory

Your memory is OptMem:
- The tool is `~/.optmem/memo`
- Every project you work in has its own memory
- One global memory, `~/.optmem/memory`, follows you into all of them

OptMem outlives every session, compaction, model and vendor change.
Without it you do not know who you are, or what was decided and tried.

### At startup: activating OptMem (mandatory)

Run `~/.optmem/memo wake` before any other tool call, in every session, and
then do exactly what it prints, to the end of its output. It reads the
global memory first, then the memory of the project you are in.

If you can see a prior OptMem wake in this conversation's history,
do not run it again.

### While working: register memories (mandatory)

Call `~/.optmem/memo note "<1 line, max 280 bytes>"` whenever you learn
something new, or something worth keeping happens. That covers a task
worth real effort, a fact or insight the user teaches you, anything you
learn about their life (even indirectly), any event of lasting effect.

That writes to the memory of the project you are in, which is where
almost everything belongs. Add `--global` ONLY if the memory would still
be true tomorrow in a repository you have never seen: who the user is,
how they want to be worked with, this machine, your own tooling. How one
project does something is not global, however much it feels like a
lesson -- write it to that project.

Do not register redundant memories.

If `~/.optmem/memo note` asks a compression: do it before your next action.

Never edit or delete a memory directory: the tool manages it.

### When you need an old memory: search, or navigate

`~/.optmem/memo recall <regex>` searches every memory, word for word. It and
`zoom` below read the project memory; put `--global` first for the
global one.

Your memories also form a binary tree: #0-1, #2-3 ... exist as one-line
summaries, pairs of those as #0-3, and so on -- every `#a-b` line wake
prints is one node of it. `~/.optmem/memo zoom <a-b>` opens a node into its
two halves, down to the raw memories.

### If you're a subagent: skip everything above

Parallel sessions on this machine are all you, and may all write memories.
A subagent is not: it must never run `memo`, because it cannot judge what
is already known, and its notes would arrive duplicated and incorrectly.
When you spawn one, write: `You are a subagent. Don't run memo.`
```
