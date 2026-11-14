# Claude Code instructions

Read and follow [AGENTS.md](AGENTS.md). [PROJECT-CONTEXT.md](PROJECT-CONTEXT.md) is the source of truth for scope.

Additional notes for Claude Code:

- Claude works with the Backend Lead on `backend/` and on `backend--dev`, or on a `docs/<topic>` branch for documentation. Do not modify `frontend/`.
- Ask before any hard-to-reverse or outward-facing action: commits, pushes, branch creation or deletion, pull requests and merges.
- Never merge or approve a pull request. Humans approve merges.
- Before editing, check `git status` and the current branch. Leave untracked files and nested clones untouched.
- When documenting, keep approved decisions separate from unresolved details.
- No application code during Phase 0. Implementation starts in Phase 1, after Phase 0 is approved and merged.
