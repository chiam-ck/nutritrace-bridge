# Hermia — NutriTrace Bridge Development Discipline

## Source of Truth

**This repo (`~/claude/nutritrace-bridge` on agentic-vm) is the single source of truth for all NutriTrace custom code:**

- `nutritrace-api.py` — REST API layer
- `nutritrace-mcp.py` — MCP server for AI agents
- `scripts/` — food DB builders, n8n setup, deployment helpers
- `src/` — supplementary code (PG adapter, etc.)
- `n8n-workflows/` — all n8n MCP webhook workflow JSONs

**GitHub `chiam-ck/nutritrace-bridge`** mirrors this repo. Always push.

## Deployment

| What | Where |
|---|---|
| **Dev repo** | agentic-vm `~/claude/nutritrace-bridge/` |
| **Deploy target** | tech-vm `~/nutritrace-deploy/` |
| **Active compose** | tech-vm `~/tech/docker-compose.yml` |
| **Data (DB + uploads)** | tech-vm `~/nutritrace-deploy/data/` |

The app container (`nutritrace`) pulls from `ghcr.io/traceapps/nutritrace:latest` — no local source code needed. The only local files are our MCP scripts.

## Development Workflow

1. **All code edits happen in this repo on agentic-vm.** Never edit `nutritrace-api.py` or `nutritrace-mcp.py` directly on tech-vm.
2. **Commit after every change.** Meaningful commit messages. Push to GitHub.
3. **Deploy with `make deploy`** — syncs the MCP files to tech-vm and restarts the containers.
4. **Sync-only** (no restart): `make sync`

## What NOT to do

- ❌ Do NOT edit MCP files on tech-vm. The next deploy overwrites them.
- ❌ There is no more `~/nutritrace/` on tech-vm — it's been replaced with the lean `~/nutritrace-deploy/`.
- ❌ Do NOT clone `TraceApps/nutritrace` — the Docker image pulls from the registry directly.
- ❌ Do NOT create separate compose files for nutritrace. Everything is in `~/tech/docker-compose.yml`.

## Quick Reference

```
make deploy       # sync + restart (full deploy)
make sync         # copy MCP files only, no restart
make test         # smoke test the API
make food-db      # rebuild food database
make logs         # tail API logs
```
