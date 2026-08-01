#!/usr/bin/env python3
"""Create NutriTrace MCP webhook workflows in n8n (5 consolidated category workflows).

Each workflow: Webhook (POST) -> Switch V3 (routes on body.op) -> per-op HTTP Request -> REST API :3002.
Consolidated Aug 2026 from 17 per-op workflows to 5 category workflows, mirroring the
native MCP server surface (nutritrace-mcp.py, 5 tools with op param).

Requires N8N_KEY env var (n8n API key for cheekong.chiam@gmail.com).
"""
import json, os, uuid, requests

API_KEY = os.environ["N8N_KEY"]
BASE = "https://tech-vm.tail3190c5.ts.net/api/v1"
HEADERS = {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}
NT = "http://100.111.123.105:3002"  # host IP, reachable from n8n's Docker network

SETTINGS = {"executionOrder": "v1", "availableInMCP": True, "callerPolicy": "workflowsFromSameOwner"}


def webhook_node(path):
    return {"parameters": {"httpMethod": "POST", "path": path, "responseMode": "lastNode", "options": {}},
            "type": "n8n-nodes-base.webhook", "typeVersion": 2.1, "position": [0, 0], "name": "Webhook"}


def switch_node(ops, x=250):
    """Switch V3 (typeVersion 3.4) — rules.values[] each with outputKey + conditions (same shape as IF)."""
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
                "options": {"fallbackOutput": "none"},
            },
            "type": "n8n-nodes-base.switch", "typeVersion": 3.4, "position": [x, 0], "name": "Switch"}


def http_node(name, method, url, query_params=None, body=None, x=500):
    p = {"method": method, "url": url, "options": {}}
    if query_params:
        p["sendQuery"] = True
        p["queryParameters"] = {"parameters": query_params}
    if body:
        p["sendBody"] = True
        p["specifyBody"] = "json"
        p["jsonBody"] = json.dumps(body)
    return {"parameters": p, "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.4,
            "position": [x, 0], "name": name}


def create(name, path, ops, http_nodes):
    nodes = [webhook_node(path), switch_node(ops)]
    nodes += http_nodes
    connections = {"Webhook": {"main": [[{"node": "Switch", "type": "main", "index": 0}]]}}
    for i, h in enumerate(http_nodes):
        # output i of Switch routes to http node i (rules order == output order)
        connections.setdefault("Switch", {"main": []})["main"].append(
            [{"node": h["name"], "type": "main", "index": 0}])
    wf = {"name": name, "settings": SETTINGS, "nodes": nodes, "connections": connections}
    r = requests.post(f"{BASE}/workflows", headers=HEADERS, json=wf)
    if r.status_code not in (200, 201):
        return print(f"❌ {name}: {r.status_code} {r.json().get('message','')}")
    wid = r.json()["id"]
    ra = requests.post(f"{BASE}/workflows/{wid}/activate", headers=HEADERS)
    if ra.status_code not in (200, 201):
        return print(f"⚠️ {name}: created but activate failed ({ra.status_code})")
    print(f"✅ {name} (id={wid})")


# Delete any stale NutriTrace workflows from previous versions (17 per-op or old 5)
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
    http_node("Add", "POST", f"{NT}/diary/add", body={
        "date": "={{$json.body.date}}",
        "food_name": "={{$json.body.food_name}}",
        "food_id": "={{$json.body.food_id}}",
        "quantity": "={{$json.body.quantity || 1}}",
        "meal": "={{$json.body.meal || 'lunch'}}"}),
    http_node("Update", "PATCH", f"={NT}/diary/{{{{$json.body.date}}}}", body={
        "food_server_id": "={{$json.body.food_server_id}}",
        "quantity": "={{$json.body.quantity}}",
        "meal": "={{$json.body.meal}}"}),
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
