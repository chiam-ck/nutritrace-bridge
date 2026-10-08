#!/usr/bin/env python3
"""Create NutriTrace MCP webhook workflows in n8n (5 consolidated category workflows).

Each workflow: Webhook (POST) -> Switch V3 (routes on body.op) -> per-op HTTP Request -> REST API :3002.
Consolidated Aug 2026 from 17 per-op workflows to 5 category workflows, mirroring the
native MCP server surface (nutritrace-mcp.py, 5 tools with op param).

Requires N8N_KEY env var (n8n API key for cheekong.chiam@gmail.com).
"""
import json, os, sys, uuid, requests

EMIT = "--emit" in sys.argv  # dump workflow JSONs to ./n8n-workflows/ instead of POSTing to the n8n API
if not EMIT:
    API_KEY = os.environ["N8N_KEY"]
BASE = "https://tech-vm.tail3190c5.ts.net/api/v1"
NT = "http://100.111.123.105:3002"  # host IP, reachable from n8n's Docker network

SETTINGS = {"executionOrder": "v1", "availableInMCP": True, "callerPolicy": "workflowsFromSameOwner"}


def webhook_node(path):
    return {"parameters": {"httpMethod": "POST", "path": path, "responseMode": "lastNode", "options": {}},
            "type": "n8n-nodes-base.webhook", "typeVersion": 2.1, "position": [0, 0], "name": "Webhook",
            "id": str(uuid.uuid4()), "webhookId": str(uuid.uuid4())}


def switch_node(ops, x=250):
    """Switch V3 (typeVersion 3.4) — rules.values[] each with outputKey + conditions (same shape as IF).

    fallbackOutput: 'extra' adds one extra output that catches unmatched items (unknown/missing op).
    Wire that final output to the "Unknown Op" Set node so the webhook returns an error instead of empty.
    """
    values = []
    for op in ops:
        values.append({
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                "conditions": [{
                    "leftValue": "={{ $json.body.op }}",
                    "rightValue": op,
                    "operator": {"type": "string", "operation": "equals"},
                }],
                "combinator": "and",
            },
            "renameOutput": False,
            "outputKey": op,
        })
    return {"parameters": {
                "mode": "rules",
                "rules": {"values": values},
                "options": {"fallbackOutput": "extra"},
            },
            "type": "n8n-nodes-base.switch", "typeVersion": 3.4, "position": [x, 0], "name": "Switch"}


def unknown_op_node(x=750):
    """Set node that emits the error JSON for unmatched ops (no API call, static output).

    SetV2 supports typeVersion 3.x ONLY (3.0/3.1/3.2/3.3/3.4) — typeVersion 2 falls back to
    Set V1 which ignores mode/jsonOutput and passes input through unchanged.
    JSON mode uses mode='raw' + jsonOutput (UI label is 'JSON' but value is 'raw').
    typeVersion 3.3+ defaults options.include to 'none', so output is just the error JSON.
    """
    return {"parameters": {
                "mode": "raw",
                "jsonOutput": '{"ok": false, "error": "unknown op"}',
            },
            "type": "n8n-nodes-base.set", "typeVersion": 3.3, "position": [x, 0], "name": "Unknown Op"}


def http_node(name, method, url, query_params=None, body=None, x=500):
    p = {"method": method, "url": url, "options": {}}
    if query_params:
        p["sendQuery"] = True
        p["queryParameters"] = {"parameters": query_params}
    if body:
        p["sendBody"] = True
        p["specifyBody"] = "json"
        p["jsonBody"] = body if isinstance(body, str) else json.dumps(body)
    return {"parameters": p, "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.4,
            "position": [x, 0], "name": name}


def create(name, path, ops, http_nodes):
    nodes = [webhook_node(path), switch_node(ops)]
    nodes += http_nodes
    nodes += [unknown_op_node(x=750)]
    connections = {"Webhook": {"main": [[{"node": "Switch", "type": "main", "index": 0}]]}}
    switch_main = []
    for i, h in enumerate(http_nodes):
        # output i of Switch routes to http node i (rules order == output order)
        switch_main.append([{"node": h["name"], "type": "main", "index": 0}])
    # fallbackOutput: 'extra' → final Switch output catches unmatched ops → Unknown Op Set node
    switch_main.append([{"node": "Unknown Op", "type": "main", "index": 0}])
    connections["Switch"] = {"main": switch_main}
    wf = {"name": name, "settings": SETTINGS, "nodes": nodes, "connections": connections}
    if EMIT:
        fname = f"{path}-mcp.json"
        with open(f"n8n-workflows/{fname}", "w") as f:
            json.dump(wf, f, indent=2, ensure_ascii=False)
        print(f"📄 emitted n8n-workflows/{fname}")
        return
    r = requests.post(f"{BASE}/workflows", headers=HEADERS, json=wf)
    if r.status_code not in (200, 201):
        return print(f"❌ {name}: {r.status_code} {r.json().get('message','')}")
    wid = r.json()["id"]
    ra = requests.post(f"{BASE}/workflows/{wid}/activate", headers=HEADERS)
    if ra.status_code not in (200, 201):
        return print(f"⚠️ {name}: created but activate failed ({ra.status_code})")
    print(f"✅ {name} (id={wid})")


# Delete any stale NutriTrace workflows from previous versions (17 per-op or old 5)
if not EMIT:
    HEADERS = {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}
    r = requests.get(f"{BASE}/workflows?limit=100", headers=HEADERS)
    for w in r.json().get("data", []):
        if "NutriTrace" in w.get("name", ""):
            requests.delete(f"{BASE}/workflows/{w['id']}", headers=HEADERS)
            print(f"🗑️ deleted stale: {w['name']}")

# --- Consolidated workflows (op-routed) ---
# Order of ops MUST match order of http_nodes below (Switch output index == rule order).

create("NutriTrace Food - MCP", "nutritrace-food", ["search", "get", "categories", "add"], [
    http_node("Search", "GET", f"{NT}/foods/search", [
        {"name": "q", "value": "={{$json.body.q}}"},
        {"name": "limit", "value": "={{$json.body.limit || '10'}}"}]),
    http_node("Get", "GET", f"={NT}/foods/{{{{$json.body.id}}}}"),
    http_node("Categories", "GET", f"{NT}/foods/categories"),
    http_node("Add", "POST", f"{NT}/foods/add", body={
        "name": "={{$json.body.name}}",
        "nutrition": "={{$json.body.nutrition}}",
        "portion": "={{$json.body.portion || 100}}",
        "unit": "={{$json.body.unit || 'g'}}",
        "category": "={{$json.body.category || ''}}",
        "brand": "={{$json.body.brand || ''}}",
        "notes": "={{$json.body.notes || ''}}",
        "barcode": "={{$json.body.barcode || ''}}"}),
])

create("NutriTrace Diary - MCP", "nutritrace-diary", ["get", "add", "update", "delete", "range"], [
    http_node("Get", "GET", f"={NT}/diary/{{{{$json.body.date}}}}"),
    http_node("Add", "POST", f"{NT}/diary/add", body="={{ JSON.stringify({ date: $json.body.date, quantity: $json.body.quantity || 1, meal: $json.body.meal || 'lunch', ...($json.body.food_name ? { food_name: $json.body.food_name } : {}), ...($json.body.food_id ? { food_id: $json.body.food_id } : {}) }) }}"),
    http_node("Update", "PATCH", f"={NT}/diary/{{{{$json.body.date}}}}", body="={{ JSON.stringify({ food_server_id: Number($json.body.food_server_id), ...($json.body.quantity != null ? { quantity: Number($json.body.quantity) } : {}), ...($json.body.meal != null ? { meal: $json.body.meal } : {}) }) }}"),
    http_node("Delete", "DELETE", f"={NT}/diary/{{{{$json.body.date}}}}", body={
        "food_server_id": "={{$json.body.food_server_id}}",
        "meal": "={{$json.body.meal}}"}),
    http_node("Range", "GET", f"{NT}/diary/range", [
        {"name": "from", "value": "={{$json.body.from}}"},
        {"name": "to", "value": "={{$json.body.to}}"}]),
])

create("NutriTrace Weight - MCP", "nutritrace-weight", ["log", "history"], [
    http_node("Log", "POST", f"{NT}/weight/log", body={
        "weight": "={{$json.body.weight}}",
        "date": "={{$json.body.date}}",
        "unit": "={{$json.body.unit || 'kg'}}",
        "notes": "={{$json.body.notes || ''}}"}),
    http_node("History", "GET", f"{NT}/weight/history"),
])

create("NutriTrace Stats - MCP", "nutritrace-stats", ["daily", "weekly", "health"], [
    http_node("Daily", "GET", f"{NT}/stats/daily", [
        {"name": "date", "value": "={{$json.body.date}}"}]),
    http_node("Weekly", "GET", f"{NT}/stats/weekly"),
    http_node("Health", "GET", f"{NT}/health"),
])

create("NutriTrace Activity - MCP", "nutritrace-activity", ["get", "log", "sum"], [
    http_node("Get", "GET", f"={NT}/activity/{{{{$json.body.date}}}}"),
    http_node("Log", "POST", f"{NT}/activity/log", body={
        "name": "={{$json.body.name}}",
        "date": "={{$json.body.date}}",
        "kcal": "={{$json.body.kcal}}",
        "duration_min": "={{$json.body.duration_min}}",
        "distance": "={{$json.body.distance || ''}}",
        "source": "={{$json.body.source || 'manual_form'}}"}),
    http_node("Sum", "GET", f"={NT}/activity/sum/{{{{$json.body.date}}}}"),
])
