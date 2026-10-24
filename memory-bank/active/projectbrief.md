# Project Brief

## User Story

As an operator whose project memory is keyed by directory path, I want that key to follow symbolic links so that one directory is one memory no matter how the working directory was spelled.

## Use-Case(s)

### Path-local scope through a symlink

A directory has no origin remote. `path_slug` is its identity. The operator reaches that directory through a symlink, a chain of symlinks, or a Windows junction. The memory is the same one as when the directory is reached by its physical path.

Authoritative statement: [issue #3](https://github.com/Texarkanine/OptMem-Split/issues/3).

## Requirements

1. Resolve symbolic links, including Windows junctions, before the path is split into the `path/` key.
2. `path_slug` of a symlink path and `path_slug` of its target are the same.
3. A chain of links (`link` → `mid` → the directory) slugs to the directory, not the link name.
4. `scope_dir` still passes `git rev-parse --show-toplevel`, or `os.getcwd()` when there is no checkout, into that function. Both inputs are resolved.

## Constraints

1. Origin-remote identity is unchanged. This applies only to the path fallback.
2. The existing Windows path encoding stays: drive letters are shaped before the path is joined under `path/`.

## Acceptance Criteria

1. Checked against `memo`: `path_slug` of a symlink path and `path_slug` of its target match. `os.path.realpath` of that symlink matches the target.
2. One directory is one memory no matter how `$PWD` was spelled.
