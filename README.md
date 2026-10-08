# NutriBridge

REST API + MCP server + n8n webhooks that let AI agents (Hermes Agent via native MCP, Claude via n8n MCP webhooks) read and write nutrition data from a self-hosted [NutriTrace](https://github.com/TraceApps/nutritrace) instance.

## What It Does

NutriTrace is a single-container nutrition tracker (Svelte + Express + SQLite). It works great for humans but ships with no API layer for agents. NutriBridge wraps it:

```
NutriTrace (:3000) ── SQLite ── NutriBridge (:3002 / :3003)
                                      │
                      ┌───────────────┴───────────────┐
                      │                               │
               Hermes Agent                       Claude
               (native MCP)                  (n8n MCP webhooks)
```

## Architecture

Single host, shared SQLite, zero pip dependencies:

```
├── nutritrace        (ghcr.io/traceapps/nutritrace)  :3000  UI
├── nutritrace-api    (python:3.11-alpine)             :3002  REST
├── nutritrace-mcp    (python:3.11-alpine)             :3003  MCP
└── nutritrace.db                                      718 foods
```

5 n8n webhook workflows (consolidated from 17, Aug 2026) provide MCP access for Claude via the same pattern used by existing Strava and Scribble Wiki integrations. Each routes on an `op` field via a Switch V3 node, mirroring the native MCP server's 5 category tools.

## Project Structure

```
├── src/
│   ├── nutritrace-api.py        REST server (stdlib, 613 lines)
│   └── nutritrace-mcp.py        MCP JSON-RPC server (stdlib, 5 category tools)
├── scripts/
│   ├── build-sg-food-db-v2.py   SG food database builder
│   └── create-nutritrace-n8n.py n8n MCP webhook factory (5 consolidated workflows)
├── n8n-workflows/               5 exportable workflow JSONs (op-routed)
├── config/
│   ├── docker-compose.yml
│   └── .env.example
└── Makefile
```

## Quick Start

```bash
cp config/.env.example .env     # set JWT_SECRET and data paths
docker compose -f config/docker-compose.yml up -d

# build food database
docker exec nutritrace python3 /tmp/build-sg-food-db-v2.py
docker exec nutritrace python3 -c "
import sqlite3; conn = sqlite3.connect('/data/db/nutritrace.db')
conn.execute('UPDATE foods SET user_id=1 WHERE user_id IS NULL')
conn.commit()"

# create n8n MCP webhooks (for Claude access)
python3 scripts/create-nutritrace-n8n.py
```

## REST API

`http://host:3002` — no auth, internal LAN, pure stdlib.

| Method | Path | Purpose |
|---:|---:|---|
| GET | `/health` | Health check |
| GET | `/weight/history` | All weight entries |
| POST | `/weight/log` | Log a weight entry |
| GET | `/diary/:date` | Diary for a date |
| POST | `/diary/add` | Log food by name |
| GET | `/foods/search?q=&limit=` | Fuzzy food search |
| GET | `/foods/:id` | Single food detail |
| GET | `/foods/categories` | All categories with counts |
| GET | `/stats/daily?date=` | Daily totals per meal (+net kcal) |
| GET | `/stats/weekly` | 7-day rollup + averages |
| GET | `/activity/:date` | Activities logged for a date |
| GET | `/activity/sum/:date` | Activity kcal (manual + wearable) |
| POST | `/activity/log` | Log a manual activity/workout |

## n8n MCP Webhooks

5 consolidated workflows exported in `n8n-workflows/` (Aug 2026). Import into n8n, enable `availableInMCP`, done. All are **POST** with a JSON body `{"op": "...", ...params}`; each routes on `op` via a Switch V3 node straight to the REST API.

| Webhook | ops |
|---|---|
| `nutritrace-food` | search, get, categories, add, update, delete |
| `nutritrace-diary` | get, add, update, delete, range |
| `nutritrace-weight` | log, history |
| `nutritrace-stats` | daily, weekly, health |
| `nutritrace-activity` | get, log, sum |

## Food Database

718 foods across 37 categories — Singapore-centric, continuously expanding:

- Hawker: rice dishes, noodle soups, fried, snacks, hot and cold drinks
- Japanese: ramen, sushi, donburi, katsu, tempura, sides
- Chinese / Zi Char: dim sum, stir-fries, noodles, congee, seafood
- Korean: BBQ, stews, fried chicken, banchan
- Western: pasta variants, burgers, steaks, salads, sandwiches
- Indian: thali, biryani, curries, naan, tandoori
- Thai, Vietnamese, Indonesian, Middle Eastern
- Fast food: McDonald's, KFC, Subway, MOS, Jollibee
- Bakery, breakfast, bubble tea, hot pot, desserts, drinks

## Known Quirks

- **Diary items are inlined full food objects** — no `food_id` field. Read nutrition directly from `item.nutrition`.
- **Nutrition key inconsistency** — most foods use `proteins`/`carbohydrates`, some use `protein`/`carbs`. Stats aggregator normalizes both.
- **Meal slots are numeric** — `0`=breakfast, `1`=lunch, `2`=dinner, `3`=snacks.
- **`diary` table has no `created_at`** — only `updated_at`.
- **Zero pip dependencies** — everything is Python stdlib.
- **n8n `bodyParameters` serializes objects as JSON strings** — the MCP server deserializes string arguments via `json.loads()` guard before dispatching tools. Without this, activity endpoints fail with `TypeError: string indices must be integers`.
- **Timezone** — all three containers run `TZ=Asia/Singapore`. The REST API uses `datetime.now()` (not `utcnow()`) so `created_at` timestamps are SGT. n8n instance timezone is also `Asia/Singapore`. Default-date fallbacks in MCP/API use `date.today()` which respects the container TZ.
- **n8n `$now.format()` uses Luxon, not moment/strftime** — `$now.format("YYYY-MM-DD")` evaluates to literal `YYYY-06-Jun 3, 2026` because `YYYY` isn't a Luxon token (passes through literally) and `DD` is a localized-date macro. Always use `yyyy-MM-dd` in n8n expressions. This was fixed in v1.1.1.

## License

MIT


## Timestamp repair and GUI overlay

The canonical local GUI repair lives in [overlays/nutritrace](overlays/nutritrace/README.md), including the pinned image build recipe, timestamp merge source, and upstream attribution. It compares legacy Singapore and timezone-aware item timestamps as instants so a fresh GUI portion edit survives the merge. The root bridge now stamps UTC item timestamps on add/PATCH, and the Diary Update workflow uses one evaluated JSON body expression.

Run `make test-timestamps` for isolated merge and bridge regressions. For the installed n8n evaluator, run `python3 tests/emit-n8n-expression-test.py | docker exec -i homelab-n8n node`; this uses synthetic payloads and executes no workflow. Deployment configuration and real diary records are not part of these tests.
