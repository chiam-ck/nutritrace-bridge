#!/usr/bin/env python3
"""
NutriTrace MCP Server — stdlib-only JSON-RPC over HTTP.
Wraps NutriTrace REST API. No SSE complexity.

5 category tools (consolidated 2026-08-01, mirroring the n8n MCP surface):
  nutritrace_food     ops: search, get, categories, add
  nutritrace_diary    ops: get, add, update, delete, range
  nutritrace_weight   ops: log, history
  nutritrace_stats    ops: daily, weekly, health
  nutritrace_activity ops: get, log, sum
Each tool takes {op: "...", ...params} — same shape as the n8n webhook workflows.
"""
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.parse import urlparse, quote
from datetime import datetime
import os

NT_API = os.environ.get("NT_API_URL", "http://127.0.0.1:3002")
PORT = int(os.environ.get("NT_MCP_PORT", 3003))

_OP = {"type": "string", "enum": []}

def _op_enum(*ops):
    return {"type": "string", "enum": list(ops)}

TOOLS = [
    {
        "name": "nutritrace_food",
        "description": "Food database operations. Pass op: search {q, limit?} searches foods by name/category; get {id} returns food by ID; categories {} lists food categories; add {name, nutrition:{calories,fat,proteins,carbs,sugar,fiber}, category, portion?, unit?, brand?, notes?, barcode?} adds a new food and returns its id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "op": _op_enum("search", "get", "categories", "add"),
                "q": {"type": "string"},
                "limit": {"type": "integer"},
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "nutrition": {"type": "object"},
                "portion": {"type": "number"},
                "unit": {"type": "string"},
                "category": {"type": "string"},
                "brand": {"type": "string"},
                "notes": {"type": "string"},
                "barcode": {"type": "string"},
            },
            "required": ["op"],
        },
    },
    {
        "name": "nutritrace_diary",
        "description": "Diary operations. Pass op: get {date} returns full diary for date; add {date?, food_name or food_id, quantity?, meal? breakfast|lunch|dinner|snacks} logs food; update {date, food_server_id, quantity?, meal?} changes portion/meal (meal numeric 0-3); delete {date, food_server_id, meal?} removes item; range {from, to} returns diaries between dates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "op": _op_enum("get", "add", "update", "delete", "range"),
                "date": {"type": "string"},
                "from": {"type": "string"},
                "to": {"type": "string"},
                "food_name": {"type": "string"},
                "food_id": {"type": "integer"},
                "quantity": {"type": "number"},
                "meal": {"type": "string"},
                "food_server_id": {"type": "integer"},
            },
            "required": ["op"],
        },
    },
    {
        "name": "nutritrace_weight",
        "description": "Weight operations. Pass op: log {weight, date?, unit?, notes?} logs a weight entry; history {} returns weight history.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "op": _op_enum("log", "history"),
                "weight": {"type": "number"},
                "date": {"type": "string"},
                "unit": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": ["op"],
        },
    },
    {
        "name": "nutritrace_stats",
        "description": "Stats and health operations. Pass op: daily {date?} returns daily nutrition summary (calories, macros, activity, net); weekly {} returns 7-day averages; health {} checks API + DB health.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "op": _op_enum("daily", "weekly", "health"),
                "date": {"type": "string"},
            },
            "required": ["op"],
        },
    },
    {
        "name": "nutritrace_activity",
        "description": "Activity/exercise operations. Pass op: get {date} lists logged activities; log {name, date?, kcal, duration_min?, distance?, source?} logs a workout; sum {date?} returns daily activity calorie summary (manual vs wearable, effective).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "op": _op_enum("get", "log", "sum"),
                "date": {"type": "string"},
                "name": {"type": "string"},
                "kcal": {"type": "integer"},
                "duration_min": {"type": "integer"},
                "distance": {"type": "string"},
                "source": {"type": "string"},
            },
            "required": ["op"],
        },
    },
]

_TODAY = lambda: datetime.now().strftime("%Y-%m-%d")


def call_api(method, path, body=None):
    url = f"{NT_API}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if body else {}
    req = Request(url, data=data, headers=headers, method=method)
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def call_tool(name, args):
    try:
        op = args.get("op")
        if name == "nutritrace_food":
            if op == "search":
                return call_api("GET", f"/foods/search?q={quote(args['q'])}&limit={args.get('limit', 20)}")
            if op == "get":
                return call_api("GET", f"/foods/{args['id']}")
            if op == "categories":
                return call_api("GET", "/foods/categories")
            if op == "add":
                return call_api("POST", "/foods/add", args)
            return {"ok": False, "error": f"unknown op: {op}"}

        if name == "nutritrace_diary":
            if op == "get":
                return call_api("GET", f"/diary/{args['date']}")
            if op == "range":
                return call_api("GET", f"/diary/range?from={args['from']}&to={args['to']}")
            if op == "add":
                body = {
                    "date": args.get("date", _TODAY()),
                    "quantity": args.get("quantity", 1),
                    "meal": args.get("meal", "lunch"),
                }
                if args.get("food_name"):
                    body["food_name"] = args["food_name"]
                if args.get("food_id"):
                    body["food_id"] = args["food_id"]
                return call_api("POST", "/diary/add", body)
            if op == "delete":
                body = {"food_server_id": args["food_server_id"]}
                if "meal" in args:
                    body["meal"] = args["meal"]
                return call_api("DELETE", f"/diary/{args['date']}", body)
            if op == "update":
                body = {"food_server_id": args["food_server_id"]}
                if "quantity" in args:
                    body["quantity"] = args["quantity"]
                if "meal" in args:
                    body["meal"] = args["meal"]
                return call_api("PATCH", f"/diary/{args['date']}", body)
            return {"ok": False, "error": f"unknown op: {op}"}

        if name == "nutritrace_weight":
            if op == "log":
                return call_api("POST", "/weight/log", {
                    "weight": args["weight"],
                    "date": args.get("date", _TODAY()),
                    "unit": args.get("unit", "kg"),
                    "notes": args.get("notes", ""),
                })
            if op == "history":
                return call_api("GET", "/weight/history")
            return {"ok": False, "error": f"unknown op: {op}"}

        if name == "nutritrace_stats":
            if op == "daily":
                return call_api("GET", f"/stats/daily?date={args.get('date', _TODAY())}")
            if op == "weekly":
                return call_api("GET", "/stats/weekly")
            if op == "health":
                return call_api("GET", "/health")
            return {"ok": False, "error": f"unknown op: {op}"}

        if name == "nutritrace_activity":
            if op == "get":
                return call_api("GET", f"/activity/{args['date']}")
            if op == "sum":
                return call_api("GET", f"/activity/sum/{args.get('date', _TODAY())}")
            if op == "log":
                return call_api("POST", "/activity/log", {
                    "name": args["name"],
                    "date": args.get("date", _TODAY()),
                    "kcal": args["kcal"],
                    "duration_min": args.get("duration_min"),
                    "distance": args.get("distance", ""),
                    "source": args.get("source", "manual_form"),
                })
            return {"ok": False, "error": f"unknown op: {op}"}

        return {"error": f"Unknown tool: {name}"}
    except Exception as e:
        return {"error": str(e)}


class MCPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{datetime.now().isoformat()}] {args[0]}", flush=True)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/")
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        if path in ("/", "/mcp", "/jsonrpc"):
            response = self._handle(body)
            self._json(response)
        elif path == "/health":
            self._json({"status": "ok", "service": "nutritrace-mcp", "tools": len(TOOLS)})
        else:
            self._json({"error": "not found"}, 404)

    def _handle(self, body):
        method = body.get("method")
        params = body.get("params", {})
        req_id = body.get("id")

        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "nutritrace-mcp", "version": "2.0.0"}
                }
            elif method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                arguments = params.get("arguments", {})
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
                tool_result = call_tool(params.get("name"), arguments)
                result = {"content": [{"type": "text", "text": json.dumps(tool_result, ensure_ascii=False)}]}
            elif method == "notifications/initialized":
                return None
            else:
                return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown: {method}"}}

            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        except Exception as e:
            print(f"ERROR: {e}", flush=True)
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32603, "message": str(e)}}

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode() if data else b""
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)


if __name__ == "__main__":
    print(f"NutriTrace MCP Server on port {PORT} (HTTP JSON-RPC)")
    print(f"  Endpoint: http://0.0.0.0:{PORT}/mcp")
    print(f"  Backend:  {NT_API}")
    print(f"  Tools:    {len(TOOLS)} (category-based)")
    server = HTTPServer(("0.0.0.0", PORT), MCPHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()
