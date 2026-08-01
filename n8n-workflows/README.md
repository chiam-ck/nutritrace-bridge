# n8n Workflow Exports

5 JSON files — clean exports of the consolidated n8n webhook workflows that power NutriBridge's MCP integration for Claude.

**Consolidated Aug 2026:** the surface went from 17 per-op workflows to 5 category workflows, each routing on an `op` field via a Switch V3 node. This mirrors the native MCP server surface (`nutritrace-mcp.py`, 5 tools with `op` param).

## Import into n8n

1. In n8n, go to **Workflows → Import from File**
2. Select the `.json` file
3. After import, set `availableInMCP: true`, `callerPolicy: workflowsFromSameOwner`
4. Click **Active** to enable the webhook

## Workflows

All are **POST** to the webhook path with a JSON body `{"op": "...", ...params}`.

| File | Webhook path | ops |
|:---|:---|:---|
| `nutritrace-food-mcp.json` | `/webhook/nutritrace-food` | search, get, categories, add |
| `nutritrace-diary-mcp.json` | `/webhook/nutritrace-diary` | get, add, update, delete, range |
| `nutritrace-weight-mcp.json` | `/webhook/nutritrace-weight` | log, history |
| `nutritrace-stats-mcp.json` | `/webhook/nutritrace-stats` | daily, weekly, health |
| `nutritrace-activity-mcp.json` | `/webhook/nutritrace-activity` | get, log, sum |

All hit the REST API at `nutritrace-api:3002` directly (no MCP JSON-RPC hop).

## Regenerate

```bash
python3 scripts/create-nutritrace-n8n.py   # requires N8N_KEY
```

## Notes

- Exported from tech-vm's n8n instance on 2026-08-01 after consolidation
- Ephemeral fields (IDs, timestamps) stripped — n8n regenerates on import
- Switch V3 (`typeVersion: 3.4`) uses `rules.values[]` — NOT the V2 `rules.rules[]` shape. Wrong schema fails activation with `Cannot read properties of undefined (reading 'execute')`
- `fallbackOutput: none` — unmatched op returns empty (no crash)
