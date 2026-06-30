#!/usr/bin/env python3
"""
NutriTrace MCP Server — stdlib-only JSON-RPC over HTTP.
Wraps NutriTrace REST API. No SSE complexity.
"""
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.parse import urlparse, quote
from datetime import datetime
import os

NT_API = os.environ.get("NT_API_URL", "http://127.0.0.1:3002")
PORT = int(os.environ.get("NT_MCP_PORT", 3003))

TOOLS = [
    {"name":"nutritrace_health","description":"Check NutriTrace API health","inputSchema":{"type":"object","properties":{},"required":[]}},
    {"name":"nutritrace_weight_history","description":"Get weight history","inputSchema":{"type":"object","properties":{},"required":[]}},
    {"name":"nutritrace_weight_log","description":"Log weight entry","inputSchema":{"type":"object","properties":{"weight":{"type":"number"},"date":{"type":"string"},"unit":{"type":"string"},"notes":{"type":"string"}},"required":["weight"]}},
    {"name":"nutritrace_diary_get","description":"Get diary for date","inputSchema":{"type":"object","properties":{"date":{"type":"string"}},"required":["date"]}},
    {"name":"nutritrace_diary_range","description":"Get diary date range","inputSchema":{"type":"object","properties":{"from":{"type":"string"},"to":{"type":"string"}},"required":["from","to"]}},
    {"name":"nutritrace_diary_add","description":"Add a food entry to diary for a date. Use food_name (fuzzy match) or food_id. meal=breakfast/lunch/dinner/snacks","inputSchema":{"type":"object","properties":{"date":{"type":"string"},"food_name":{"type":"string"},"food_id":{"type":"integer"},"quantity":{"type":"number"},"meal":{"type":"string","enum":["breakfast","lunch","dinner","snacks"]}},"required":["date"]}},
    {"name":"nutritrace_foods_search","description":"Search foods","inputSchema":{"type":"object","properties":{"q":{"type":"string"},"limit":{"type":"integer"}},"required":["q"]}},
    {"name":"nutritrace_foods_get","description":"Get food by ID","inputSchema":{"type":"object","properties":{"id":{"type":"integer"}},"required":["id"]}},
    {"name":"nutritrace_foods_categories","description":"List food categories","inputSchema":{"type":"object","properties":{},"required":[]}},
    {"name":"nutritrace_foods_add","description":"Add food to database","inputSchema":{"type":"object","properties":{"name":{"type":"string"},"nutrition":{"type":"object"},"portion":{"type":"number"},"unit":{"type":"string"},"category":{"type":"string"},"brand":{"type":"string"},"notes":{"type":"string"},"barcode":{"type":"string"}},"required":["name","nutrition"]}},
    {"name":"nutritrace_stats_daily","description":"Daily nutrition summary","inputSchema":{"type":"object","properties":{"date":{"type":"string"}},"required":[]}},
    {"name":"nutritrace_stats_weekly","description":"7-day nutrition averages","inputSchema":{"type":"object","properties":{},"required":[]}},
    {"name":"nutritrace_activity_get","description":"Get logged activities for a date","inputSchema":{"type":"object","properties":{"date":{"type":"string"}},"required":["date"]}},
    {"name":"nutritrace_activity_sum","description":"Get daily activity calorie summary (manual + wearable)","inputSchema":{"type":"object","properties":{"date":{"type":"string"}},"required":[]}},
    {"name":"nutritrace_activity_log","description":"Log a manual activity/workout","inputSchema":{"type":"object","properties":{"date":{"type":"string"},"name":{"type":"string"},"kcal":{"type":"integer"},"duration_min":{"type":"integer"},"distance":{"type":"string"}},"required":["date","name","kcal"]}}
]


def call_api(method, path, body=None):
    url = f"{NT_API}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if body else {}
    req = Request(url, data=data, headers=headers, method=method)
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def call_tool(name, args):
    try:
        if name == "nutritrace_health":
            return call_api("GET", "/health")
        elif name == "nutritrace_weight_history":
            return call_api("GET", "/weight/history")
        elif name == "nutritrace_weight_log":
            return call_api("POST", "/weight/log", {
                "weight": args["weight"],
                "date": args.get("date", datetime.now().strftime("%Y-%m-%d")),
                "unit": args.get("unit", "kg"),
                "notes": args.get("notes", "")
            })
        elif name == "nutritrace_diary_get":
            return call_api("GET", f"/diary/{args['date']}")
        elif name == "nutritrace_diary_range":
            return call_api("GET", f"/diary/range?from={args['from']}&to={args['to']}")
        elif name == "nutritrace_diary_add":
            return call_api("POST", "/diary/add", {
                "date": args.get("date", datetime.now().strftime("%Y-%m-%d")),
                "food_name": args.get("food_name"),
                "food_id": args.get("food_id"),
                "quantity": args.get("quantity", 1),
                "meal": args.get("meal", "lunch")
            })
        elif name == "nutritrace_foods_search":
            limit = args.get("limit", 20)
            return call_api("GET", f"/foods/search?q={quote(args['q'])}&limit={limit}")
        elif name == "nutritrace_foods_get":
            return call_api("GET", f"/foods/{args['id']}")
        elif name == "nutritrace_foods_categories":
            return call_api("GET", "/foods/categories")
        elif name == "nutritrace_foods_add":
            return call_api("POST", "/foods/add", args)
        elif name == "nutritrace_stats_daily":
            date = args.get("date", datetime.now().strftime("%Y-%m-%d"))
            return call_api("GET", f"/stats/daily?date={date}")
        elif name == "nutritrace_stats_weekly":
            return call_api("GET", "/stats/weekly")

        elif name == "nutritrace_activity_get":
            return call_api("GET", f"/activity/{args['date']}")
        elif name == "nutritrace_activity_sum":
            date = args.get("date", datetime.now().strftime("%Y-%m-%d"))
            return call_api("GET", f"/activity/sum/{date}")
        elif name == "nutritrace_activity_log":
            return call_api("POST", "/activity/log", {
                "name": args["name"],
                "date": args.get("date", datetime.now().strftime("%Y-%m-%d")),
                "kcal": args["kcal"],
                "duration_min": args.get("duration_min"),
                "distance": args.get("distance", "")
            })
        else:
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
            self._json({"status": "ok", "service": "nutritrace-mcp"})
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
                    "serverInfo": {"name": "nutritrace-mcp", "version": "1.0.0"}
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
    server = HTTPServer(("0.0.0.0", PORT), MCPHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()
