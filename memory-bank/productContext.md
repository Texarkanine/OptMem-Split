# Product Context

## Target Audience

People who run AI coding agents across several projects and want those agents to remember durable facts without mixing every project's history into one log. Operators install a small tool and paste a short instruction block into the agent's prompt file.

## Use Cases

- Start a session by reading who the operator is, then what this project has already decided and tried.
- Record one short fact while working, in the project that produced it.
- Reach a smaller set of facts that should follow the operator into every repository (how they work, this machine, tooling).
- Search or walk older memories when the recent summary is not enough.
- Relocate the global store (for example to a synced folder) independently of per-project stores.

## Key Benefits

- Project memory does not decay at the rate of every other project.
- One repo is one memory across worktrees, hosts, and remote URL spellings.
- Nothing runs in the background; the agent is told the next command when a merge is due.
- The tool is one Python file with no dependencies.

## Success Criteria

- A fresh checkout remembers into its own store on first use, without a separate init ceremony.
- Global memory exists only after a deliberate init, so a typo does not open a second empty identity.
- Wake output fits the reading budgets of the agent harnesses in use.
- The same origin remote, however it is spelled, shares one project memory.

## Key Constraints

- One line per memory, short enough to stay a single record.
- The agent, not a daemon, performs compressions when asked.
- Integration is a pasted prompt plus a script; no service, no account, no network after install.
- Upstream OptMem remains a single-store tool; this fork splits project and global stores and requires an explicit scope on store commands.
