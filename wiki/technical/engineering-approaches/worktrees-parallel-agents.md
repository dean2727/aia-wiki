# Worktrees for Parallel Agents

> Dean's git-worktree convention for running multiple coding agents (Cursor, Devin, …) in parallel on isolated branches without them stepping on each other.

**Category**: tools
**Last updated**: 2026-05-25
**Status**: reference

## What it is

A standing rule (`alwaysApply: true`) for parallelizing agent work via git worktrees kept inside the repo under `.worktrees/<name>/` (gitignored, so checkout contents never get committed). Every worktree branches from `main`, tracks `main` while in progress, and merges back into `main` — local merge or PR. Each worktree is its own tree, so per-tree setup is required: run `npm install` under `frontend/`, set up the backend venv, and copy or symlink the gitignored `.env`/`.env.local`. Supabase migrations in `supabase/migrations/` are shared, so parallel branches must use distinct timestamped filenames to avoid collisions.

It's the mechanism that makes parallel [[vibe-coding]] safe and the natural companion to the wave structure in [[starting-a-project-vibe-coding]].

## Why it matters

Running two agents in one checkout means they overwrite each other's edits and fight over branch state. Worktrees give each stream a physically separate working directory on its own branch — true parallelism with clean isolation. The division of labor is the key discipline: **Dean owns branches, environments, and integration; the agent owns implementation and verification inside the scopes he defines.** Agents only run in parallel when scopes are genuinely non-overlapping; otherwise they sequence and say why.

## How it works

| Action | Command / rule |
|---|---|
| Create | `git worktree add -b stage/next .worktrees/next main` |
| Attach to existing branch | `git worktree add .worktrees/next stage/next` |
| Per-tree setup | `npm install` in `frontend/`, backend venv, copy/symlink `.env`; pick distinct ports if two dev servers run |
| Supabase | Shared migrations — use distinct timestamped filenames per branch |
| Merge back | Sync `main` ← `origin`; `git merge main` into worktree; merge `stage/next` → `main` (or open a PR) |
| Cleanup | `git worktree remove [--force] .worktrees/next`; `git branch -d stage/next`; `git worktree prune` if dir deleted manually |

Naming: stage branches `stage/<name>`, features `feature/<name>`, dirs `.worktrees/<name>/`.

**Parallel pattern:** "Piece A → worktree A; Piece B → worktree B" — agent runs them concurrently only if scopes are separated, else sequences. A tmux config (smart splits, Option+arrow pane nav) and a `tmux4.sh` four-pane launcher are kept in `~/` for driving several streams at once.

## Related
- [[starting-a-project-vibe-coding]]
- [[vibe-coding]]
- [[spec-driven-development]]
- [[skills-rules-subagents]]
