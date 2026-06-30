#!/usr/bin/env python3
"""
NutriTrace Data API — PostgreSQL edition.
Runs on tech-vm, reads NutriTrace data from Postgres.
No dependencies outside psycopg2 + stdlib. No auth (internal LAN only).

Endpoints:
  GET  /health
  GET  /weight/history          — weight entries over time
  POST /weight/log              — log a weight entry
  GET  /diary/:date             — full diary for a date
  GET  /diary/range?from=&to=   — diary date range
  GET  /foods/search?q=         — search foods
  GET  /foods/:id               — single food by id
  GET  /stats/daily?date=       — daily nutrition summary
  GET  /stats/weekly            — last 7 days aggregate
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta, date

import psycopg2
import psycopg2.extras

# PostgreSQL connection
PG_HOST = os.environ.get("PG_HOST", "postgres")
PG_PORT = int(os.environ.get("PG_PORT", 5432))
PG_DB = os.environ.get("PG_DB", "nutritrace")
PG_USER = os.environ.get("PG_USER", "nutritrace")
PG_PASS = os.environ.get("PG_PASS")  # required — provide via env / .env, never hardcode

PORT = int(os.environ.get("NT_API_PORT", 3002))


def get_db():
    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DB,
        user=PG_USER, password=PG_PASS
    )
    conn.autocommit = True
    return conn


def json_response(handler, data, status=200):
    body = json.dumps(data, default=str, ensure_ascii=False).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def parse_body(handler):
    length = int(handler.headers.get("Content-Length", 0))
    if length == 0:
        return {}
    return json.loads(handler.rfile.read(length))


class APIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{datetime.now().isoformat()}] {args[0]}", flush=True)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)

        try:
            if path == "/health":
                db = get_db()
                cur = db.cursor()
                cur.execute("SELECT 1")
                cur.close()
                db.close()
                return json_response(self, {"status": "ok", "db": "postgres"})

            # ── ACTIVITY ──
            elif path.startswith("/activity/sum/"):
                date_str = path.split("/activity/sum/")[1]
                db = get_db()
                cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(
                    "SELECT COALESCE(SUM(kcal), 0) AS s FROM activity_log WHERE user_id=1 AND date=%s AND deleted_at IS NULL",
                    (date_str,)
                )
                manual_row = cur.fetchone()
                cur.execute(
                    "SELECT MAX(value) AS v FROM wellness_data WHERE user_id=1 AND date=%s AND metric_type='active_calories'",
                    (date_str,)
                )
                wearable_row = cur.fetchone()
                cur.close()
                db.close()
                manual = int(manual_row["s"] or 0)
                wearable = int(wearable_row["v"] or 0) if wearable_row else 0
                effective = max(manual, wearable)
                return json_response(self, {
                    "date": date_str,
                    "manual": manual,
                    "wearable": wearable,
                    "effective": effective
                })

            elif path.startswith("/activity/"):
                date_str = path.split("/activity/")[1]
                db = get_db()
                cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(
                    """SELECT id, date, name, kcal, duration_min, distance, source, created_at
                       FROM activity_log WHERE user_id=1 AND date=%s AND deleted_at IS NULL
                       ORDER BY id ASC""",
                    (date_str,)
                )
                rows = cur.fetchall()
                cur.close()
                db.close()
                return json_response(self, [dict(r) for r in rows])

            # ── WEIGHT ──
            elif path == "/weight/history":
                db = get_db()
                cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(
                    """SELECT date, body_stats FROM diary 
                       WHERE user_id=1 AND deleted_at IS NULL 
                       AND body_stats IS NOT NULL AND body_stats != '{}'
                       ORDER BY date ASC"""
                )
                rows = cur.fetchall()
                cur.close()
                db.close()
                weights = []
                for r in rows:
                    bs = json.loads(r["body_stats"])
                    if "weight" in bs:
                        weights.append({
                            "date": r["date"],
                            "weight": bs["weight"],
                            "unit": bs.get("weight_unit", "kg"),
                            "notes": bs.get("notes", "")
                        })
                return json_response(self, {"weights": weights, "count": len(weights)})

            # ── DIARY ──
            elif path == "/diary":
                date_str = params.get("date", [None])[0]
                if not date_str:
                    return json_response(self, {"error": "?date=YYYY-MM-DD required"}, 400)
                db = get_db()
                cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(
                    """SELECT * FROM diary
                       WHERE user_id=1 AND date=%s AND deleted_at IS NULL""",
                    (date_str,)
                )
                row = cur.fetchone()
                cur.close()
                db.close()
                if not row:
                    return json_response(self, {"date": date_str, "items": [], "body_stats": {},
                                                 "water": [], "notes": ""})
                return json_response(self, _parse_diary_row(row))

            elif path.startswith("/diary/range"):
                from_date = params.get("from", [None])[0]
                to_date = params.get("to", [None])[0]
                if not from_date or not to_date:
                    return json_response(self, {"error": "from and to required"}, 400)
                db = get_db()
                cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(
                    """SELECT * FROM diary 
                       WHERE user_id=1 AND deleted_at IS NULL 
                       AND date >= %s AND date <= %s
                       ORDER BY date ASC""",
                    (from_date, to_date)
                )
                rows = cur.fetchall()
                cur.close()
                db.close()
                return json_response(self, {
                    "entries": [_parse_diary_row(r) for r in rows],
                    "from": from_date, "to": to_date, "count": len(rows)
                })

            elif path.startswith("/diary/"):
                date_str = path.split("/diary/")[1]
                db = get_db()
                cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(
                    """SELECT * FROM diary 
                       WHERE user_id=1 AND date=%s AND deleted_at IS NULL""",
                    (date_str,)
                )
                row = cur.fetchone()
                cur.close()
                db.close()
                if not row:
                    return json_response(self, {"date": date_str, "items": [], "body_stats": {},
                                                 "water": [], "notes": ""})
                return json_response(self, _parse_diary_row(row))

            # ── FOODS ──
            elif path == "/foods/categories":
                db = get_db()
                cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(
                    """SELECT category, COUNT(*) as count 
                       FROM foods WHERE user_id=1 AND deleted_at IS NULL AND category IS NOT NULL
                       GROUP BY category ORDER BY category"""
                )
                rows = cur.fetchall()
                cur.close()
                db.close()
                return json_response(self, {"categories": [{"name": r["category"], "count": r["count"]} for r in rows]})

            elif path.startswith("/foods/search"):
                q = params.get("q", [""])[0]
                limit = min(int(params.get("limit", [20])[0]), 100)
                db = get_db()
                cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                if q:
                    cur.execute(
                        """SELECT id, name, brand, category, nutrition, portion, unit, notes
                           FROM foods WHERE user_id=1 AND deleted_at IS NULL 
                           AND (name ILIKE %s OR category ILIKE %s OR brand ILIKE %s)
                           ORDER BY usage_count DESC, name ASC LIMIT %s""",
                        (f"%{q}%", f"%{q}%", f"%{q}%", limit)
                    )
                else:
                    cur.execute(
                        """SELECT id, name, brand, category, nutrition, portion, unit, notes
                           FROM foods WHERE user_id=1 AND deleted_at IS NULL
                           ORDER BY name ASC LIMIT %s""",
                        (limit,)
                    )
                rows = cur.fetchall()
                cur.close()
                db.close()
                return json_response(self, {
                    "foods": [_parse_food_row(r) for r in rows],
                    "count": len(rows)
                })

            elif path.startswith("/foods/"):
                fid = int(path.split("/foods/")[1])
                db = get_db()
                cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(
                    "SELECT * FROM foods WHERE user_id=1 AND id=%s AND deleted_at IS NULL",
                    (fid,)
                )
                row = cur.fetchone()
                cur.close()
                db.close()
                if not row:
                    return json_response(self, {"error": "not found"}, 404)
                return json_response(self, _parse_food_row(row))

            # ── STATS ──
            elif path == "/stats/daily":
                date_str = params.get("date", [date.today().isoformat()])[0]
                db = get_db()
                cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(
                    """SELECT date, items, body_stats, water, notes 
                       FROM diary WHERE user_id=1 AND date=%s AND deleted_at IS NULL""",
                    (date_str,)
                )
                row = cur.fetchone()
                cur.close()
                db.close()
                if not row:
                    empty_summary = {"date": date_str, "meals": {}, "totals": {
                        "calories": 0, "protein": 0, "carbs": 0, "fat": 0,
                        "fiber": 0, "sodium": 0, "water_ml": 0
                    }}
                    db2 = get_db()
                    cur2 = db2.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    cur2.execute(
                        "SELECT COALESCE(SUM(kcal), 0) AS s FROM activity_log WHERE user_id=1 AND date=%s AND deleted_at IS NULL",
                        (date_str,)
                    )
                    act_row = cur2.fetchone()
                    cur2.close()
                    db2.close()
                    empty_summary["activity_kcal"] = int(act_row["s"] or 0)
                    empty_summary["net_kcal"] = 0 - empty_summary["activity_kcal"]
                    return json_response(self, empty_summary)
                summary = _compute_daily_summary(row)
                db2 = get_db()
                cur2 = db2.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur2.execute(
                    "SELECT COALESCE(SUM(kcal), 0) AS s FROM activity_log WHERE user_id=1 AND date=%s AND deleted_at IS NULL",
                    (date_str,)
                )
                act_row = cur2.fetchone()
                cur2.execute(
                    "SELECT MAX(value) AS v FROM wellness_data WHERE user_id=1 AND date=%s AND metric_type='active_calories'",
                    (date_str,)
                )
                wear_row = cur2.fetchone()
                cur2.close()
                db2.close()
                summary["activity_kcal"] = max(int(act_row["s"] or 0), int(wear_row["v"] or 0) if wear_row else 0)
                summary["net_kcal"] = summary["totals"]["calories"] - summary["activity_kcal"]
                return json_response(self, summary)

            elif path == "/stats/weekly":
                end = date.today()
                start = end - timedelta(days=6)
                db = get_db()
                cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(
                    """SELECT * FROM diary 
                       WHERE user_id=1 AND deleted_at IS NULL 
                       AND date >= %s AND date <= %s
                       ORDER BY date ASC""",
                    (start.isoformat(), end.isoformat())
                )
                rows = cur.fetchall()
                cur.close()
                db.close()
                summaries = {}
                for r in rows:
                    summaries[r["date"]] = _compute_daily_summary(r)
                return json_response(self, {
                    "from": start.isoformat(),
                    "to": end.isoformat(),
                    "days": summaries,
                    "averages": _compute_weekly_averages(summaries)
                })

            else:
                return json_response(self, {"error": "not found"}, 404)

        except Exception as e:
            print(f"ERROR: {e}", flush=True)
            return json_response(self, {"error": str(e)}, 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        try:
            if path == "/diary/add":
                body = parse_body(self)
                date_str = body.get("date", date.today().isoformat())
                food_name = body.get("food_name")
                food_id = body.get("food_id")
                quantity = float(body.get("quantity", 1))
                meal_name = body.get("meal", "lunch").lower()

                if not food_name and not food_id:
                    return json_response(self, {"error": "food_name or food_id required"}, 400)

                db = get_db()
                cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                food = None
                if food_name:
                    cur.execute(
                        "SELECT * FROM foods WHERE user_id=1 AND deleted_at IS NULL AND name ILIKE %s LIMIT 1",
                        (f"%{food_name}%",)
                    )
                    food = cur.fetchone()
                if not food and food_id:
                    cur.execute(
                        "SELECT * FROM foods WHERE id=%s AND user_id=1 AND deleted_at IS NULL",
                        (food_id,)
                    )
                    food = cur.fetchone()
                if not food:
                    cur.close()
                    db.close()
                    return json_response(self, {"error": f"Food not found: {food_name or food_id}", "hint": "Try /foods/search?q=... to find the right name"}, 404)

                MEAL_MAP = {"breakfast": 0, "lunch": 1, "dinner": 2, "snacks": 3, "snack": 3}
                meal_slot = MEAL_MAP.get(meal_name, 1)
                now_ts = datetime.now().isoformat()

                new_item = {
                    "id": food["id"],
                    "user_id": 1,
                    "name": food["name"],
                    "brand": food["brand"],
                    "nutrition": json.loads(food["nutrition"] or "{}"),
                    "portion": food["portion"],
                    "unit": food["unit"],
                    "notes": food["notes"],
                    "barcode": food["barcode"],
                    "category": food["category"],
                    "favorite": bool(food["favorite"]),
                    "quantity": quantity,
                    "meal": meal_slot,
                    "addedAt": now_ts,
                    "food_server_id": food["id"],
                }

                cur.execute(
                    "SELECT id, items FROM diary WHERE user_id=1 AND date=%s AND deleted_at IS NULL",
                    (date_str,)
                )
                existing = cur.fetchone()

                if existing:
                    items = json.loads(existing["items"] or "[]")
                    items.append(new_item)
                    cur.execute(
                        "UPDATE diary SET items=%s, updated_at=%s WHERE id=%s",
                        (json.dumps(items), now_ts, existing["id"])
                    )
                else:
                    items = [new_item]
                    cur.execute(
                        "INSERT INTO diary (user_id, date, items, body_stats, water, notes, updated_at) VALUES (1, %s, %s, '{}', '[]', '', %s)",
                        (date_str, json.dumps(items), now_ts)
                    )

                cur.execute(
                    "UPDATE foods SET usage_count = usage_count + 1, last_used_at = %s WHERE id=%s",
                    (date_str, food["id"])
                )
                cur.close()
                db.close()
                return json_response(self, {
                    "ok": True,
                    "date": date_str,
                    "added": {"name": food["name"], "quantity": quantity, "meal": meal_name},
                    "total_items": len(items),
                })

            elif path == "/weight/log":
                body = parse_body(self)
                weight = body.get("weight")
                date_str = body.get("date", date.today().isoformat())
                unit = body.get("unit", "kg")
                notes = body.get("notes", "")

                if not weight:
                    return json_response(self, {"error": "weight required"}, 400)

                db = get_db()
                cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(
                    "SELECT id, body_stats FROM diary WHERE user_id=1 AND date=%s AND deleted_at IS NULL",
                    (date_str,)
                )
                existing = cur.fetchone()

                now = datetime.now().isoformat()
                if existing:
                    bs = json.loads(existing["body_stats"]) if existing["body_stats"] else {}
                    bs["weight"] = weight
                    bs["weight_unit"] = unit
                    cur.execute(
                        "UPDATE diary SET body_stats=%s, updated_at=%s WHERE id=%s",
                        (json.dumps(bs), now, existing["id"])
                    )
                else:
                    bs = json.dumps({"weight": weight, "weight_unit": unit})
                    cur.execute(
                        """INSERT INTO diary (user_id, date, items, body_stats, water, notes, updated_at)
                           VALUES (1, %s, '[]', %s, '[]', %s, %s)""",
                        (date_str, bs, notes, now)
                    )
                cur.close()
                db.close()
                return json_response(self, {"ok": True, "date": date_str, "weight": weight, "unit": unit})

            elif path == "/activity/log":
                body = parse_body(self)
                name = str(body.get("name", "")).strip()[:80]
                date_str = body.get("date", date.today().isoformat())
                kcal = max(0, int(body.get("kcal", 0)))
                duration_min = body.get("duration_min")
                distance = str(body.get("distance", ""))[:40] or None
                source = body.get("source", "manual_form")
                if source not in ("manual_form", "ai_estimated", "user_stated"):
                    source = "manual_form"
                if not name:
                    return json_response(self, {"error": "name required"}, 400)

                db = get_db()
                cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                now = datetime.now().isoformat()
                cur.execute(
                    """INSERT INTO activity_log (user_id, date, name, kcal, duration_min, distance, source, created_at, updated_at)
                       VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s)
                       RETURNING *""",
                    (date_str, name, kcal, duration_min, distance, source, now, now)
                )
                row = cur.fetchone()
                cur.close()
                db.close()
                return json_response(self, dict(row), 201)

            else:
                return json_response(self, {"error": "not found"}, 404)

        except Exception as e:
            print(f"ERROR: {e}", flush=True)
            return json_response(self, {"error": str(e)}, 500)


# ── Helpers ──

def _parse_diary_row(row):
    return {
        "id": row["id"],
        "date": row["date"],
        "items": json.loads(row["items"] or "[]"),
        "body_stats": json.loads(row["body_stats"] or "{}"),
        "water": json.loads(row["water"] or "[]"),
        "notes": row["notes"] or "",
        "updated_at": row.get("updated_at"),
    }


def _parse_food_row(row):
    return {
        "id": row.get("id"),
        "name": row.get("name"),
        "brand": row.get("brand"),
        "category": row.get("category"),
        "nutrition": json.loads(row.get("nutrition") or "{}"),
        "portion": row.get("portion"),
        "unit": row.get("unit"),
        "notes": row.get("notes"),
        "barcode": row.get("barcode"),
        "favorite": bool(row.get("favorite", 0)),
        "usage_count": row.get("usage_count", 0),
    }


MEAL_NAMES = {0: "breakfast", 1: "lunch", 2: "dinner", 3: "snacks"}


def _normalize_nutrition(nutrition):
    if not nutrition:
        return {}
    n = dict(nutrition)
    if "proteins" in n and "protein" not in n:
        n["protein"] = n.pop("proteins")
    if "carbohydrates" in n and "carbs" not in n:
        n["carbs"] = n.pop("carbohydrates")
    if "carbs" in n and "carbohydrates" not in n:
        n["carbohydrates"] = n["carbs"]
    if "sugar" in n and "sugars" not in n:
        n["sugars"] = n["sugar"]
    return n


def _compute_daily_summary(row):
    items = json.loads(row["items"] or "[]")
    water = json.loads(row["water"] or "[]")
    body_stats = json.loads(row["body_stats"] or "{}")

    totals = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0, "sodium": 0}
    meals = {}

    for item in items:
        name = item.get("name", "unknown")
        qty = item.get("quantity", 1) or 1
        nutrition = _normalize_nutrition(item.get("nutrition"))

        meal_idx = item.get("meal", 0)
        if isinstance(meal_idx, (int, float)):
            meal = MEAL_NAMES.get(int(meal_idx), f"meal_{int(meal_idx)}")
        else:
            meal = str(meal_idx).lower() if meal_idx else "other"

        cals = nutrition.get("calories", 0) * qty
        prot = nutrition.get("protein", 0) * qty or nutrition.get("proteins", 0) * qty
        carbs = (nutrition.get("carbs", 0) or nutrition.get("carbohydrates", 0)) * qty
        fat = nutrition.get("fat", 0) * qty
        fiber = nutrition.get("fiber", 0) * qty
        sodium = nutrition.get("sodium", 0) * qty

        totals["calories"] += cals
        totals["protein"] += prot
        totals["carbs"] += carbs
        totals["fat"] += fat
        totals["fiber"] += fiber
        totals["sodium"] += sodium

        if meal not in meals:
            meals[meal] = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0, "items": []}
        meals[meal]["calories"] += cals
        meals[meal]["protein"] += prot
        meals[meal]["carbs"] += carbs
        meals[meal]["fat"] += fat
        meals[meal]["items"].append({
            "name": name,
            "quantity": qty,
            "calories": round(cals),
            "protein": round(prot, 1),
            "carbs": round(carbs, 1),
            "fat": round(fat, 1),
        })

    for k in totals:
        totals[k] = round(totals[k])
    for m in meals.values():
        for k in ("calories", "protein", "carbs", "fat"):
            m[k] = round(m[k])

    water_ml = sum(w.get("amount", 0) for w in water)

    return {
        "date": row["date"],
        "meals": meals,
        "totals": totals,
        "water_ml": water_ml,
        "body_stats": body_stats,
        "notes": row["notes"] or "",
    }


def _compute_weekly_averages(summaries):
    if not summaries:
        return {}
    days = len(summaries)
    avgs = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0, "sodium": 0, "water_ml": 0}
    for d in summaries.values():
        t = d["totals"]
        for k in avgs:
            if k == "water_ml":
                avgs[k] += d.get("water_ml", 0)
            else:
                avgs[k] += t.get(k, 0)
    for k in avgs:
        avgs[k] = round(avgs[k] / days) if days > 0 else 0
    return avgs


if __name__ == "__main__":
    print(f"Starting NutriTrace API (PostgreSQL) on port {PORT}...")
    server = HTTPServer(("0.0.0.0", PORT), APIHandler)
    print(f"Listening on http://0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()
