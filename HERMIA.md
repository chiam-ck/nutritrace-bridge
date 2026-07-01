# Hermia — NutriTrace Bridge Development Discipline

## Source of Truth

**This repo (`~/claude/nutritrace-bridge` on agentic-vm) is the single source of truth for all NutriTrace custom code:**

- `nutritrace-api.py` — REST API layer (custom, not upstream)
- `nutritrace-mcp.py` — MCP server for AI agents
- `scripts/` — food DB builders, n8n setup, deployment helpers
- `src/` — supplementary code (PG adapter, etc.)
- `n8n-workflows/` — all n8n MCP webhook workflow JSONs

**GitHub `chiam-ck/nutritrace-bridge`** mirrors this repo. Always push.

## What Lives Where

| Host | Path | Purpose |
|---|---|---|
| **agentic-vm** | `~/claude/nutritrace-bridge/` | **Dev + source of truth** — all code changes happen here |
| **tech-vm** | `~/nutritrace/` | **Deployment target only** — upstream NutriTrace app + synced MCP files |
| **tech-vm** | `~/tech/docker-compose.yml` | **Active compose** — manages all tech-vm services including nutritrace×3 |

## Development Workflow

1. **All code edits happen in this repo on agentic-vm.** Never edit `nutritrace-api.py` or `nutritrace-mcp.py` directly on tech-vm.
2. **Commit after every change.** Meaningful commit messages. Push to GitHub.
3. **Deploy with `make deploy`** — this syncs the MCP files to tech-vm and restarts the containers.
4. **If you only need to sync files** (no restart), use `make sync`.

## What NOT to do

- ❌ Do NOT edit `nutritrace-api.py` or `nutritrace-mcp.py` on tech-vm. Changes will be overwritten by the next deploy.
- ❌ Do NOT put bridge-owned files into tech-vm's `~/nutritrace/` directory. That repo tracks the upstream NutriTrace app (`TraceApps/nutritrace`), not our custom code.
- ❌ Do NOT create docker-compose files for nutritrace on tech-vm. The active compose is `~/tech/docker-compose.yml` (managed by PennyClaw).

## Quick Reference

```
make deploy       # sync + restart (full deploy)
make sync         # copy MCP files only, no restart
make test         # smoke test the API
make food-db      # rebuild food database
make logs         # tail API logs
```
