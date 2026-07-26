#!/usr/bin/env python3
"""
NutriTrace Data API — lightweight stdlib-only HTTP server.
Runs on tech-vm, reads NutriTrace SQLite directly.
No dependencies. No auth (internal LAN only).

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
  DELETE /diary/:date          — remove item (body: {food_server_id, meal?})
  PATCH  /diary/:date          — update item (body: {food_server_id, quantity?, meal?})
"""

import sqlite3
import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta, date

DB_PATH = os.environ.get("NT_DB_PATH", "/data/db/nutritrace.db")
PORT = int(os.environ.get("NT_API_PORT", 3002))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
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
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)

        try:
            if path == "/health":
                db = get_db()
                db.execute("SELECT 1")
                db.close()
                return json_response(self, {"status": "ok", "db": "connected"})


            # ── ACTIVITY ──
            elif path.startswith("/activity/sum/"):
                date_str = path.split("/activity/sum/")[1]
                db = get_db()
                manual_row = db.execute(
                    "SELECT COALESCE(SUM(kcal), 0) AS s FROM activity_log WHERE user_id=1 AND date=? AND deleted_at IS NULL",
                    (date_str,)
                ).fetchone()
                wearable_row = db.execute(
                    "SELECT MAX(value) AS v FROM wellness_data WHERE user_id=1 AND date=? AND metric_type='active_calories'",
                    (date_str,)
                ).fetchone()
                db.close()
                manual = int(manual_row["s"] or 0)
                wearable = int(wearable_row["v"] or 0)
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
                rows = db.execute(
                    """SELECT id, date, name, kcal, duration_min, distance, source, created_at
                       FROM activity_log WHERE user_id=1 AND date=? AND deleted_at IS NULL
                       ORDER BY id ASC""",
                    (date_str,)
                ).fetchall()
                db.close()
                return json_response(self, [dict(r) for r in rows])

            # ── WEIGHT ──
            elif path == "/weight/history":
                db = get_db()
                rows = db.execute(
                    """SELECT date, body_stats FROM diary 
                       WHERE user_id=1 AND deleted_at IS NULL 
                       AND body_stats IS NOT NULL AND body_stats != '{}'
                       ORDER BY date ASC"""
                ).fetchall()
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
                # Query param style: /diary?date=2026-05-31
                date_str = params.get("date", [None])[0]
                if not date_str:
                    return json_response(self, {"error": "?date=YYYY-MM-DD required"}, 400)
                db = get_db()
                row = db.execute(
                    """SELECT * FROM diary
                       WHERE user_id=1 AND date=? AND deleted_at IS NULL""",
                    (date_str,)
                ).fetchone()
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
                rows = db.execute(
                    """SELECT * FROM diary 
                       WHERE user_id=1 AND deleted_at IS NULL 
                       AND date >= ? AND date <= ?
                       ORDER BY date ASC""",
                    (from_date, to_date)
                ).fetchall()
                db.close()
                return json_response(self, {
                    "entries": [_parse_diary_row(r) for r in rows],
                    "from": from_date, "to": to_date, "count": len(rows)
                })

            elif path.startswith("/diary/"):
                date_str = path.split("/diary/")[1]
                db = get_db()
                row = db.execute(
                    """SELECT * FROM diary 
                       WHERE user_id=1 AND date=? AND deleted_at IS NULL""",
                    (date_str,)
                ).fetchone()
                db.close()
                if not row:
                    return json_response(self, {"date": date_str, "items": [], "body_stats": {},
                                                 "water": [], "notes": ""})
                return json_response(self, _parse_diary_row(row))

            # ── FOODS ──
            elif path == "/foods/categories":
                db = get_db()
                rows = db.execute(
                    """SELECT category, COUNT(*) as count 
                       FROM foods WHERE user_id=1 AND deleted_at IS NULL AND category IS NOT NULL
                       GROUP BY category ORDER BY category"""
                ).fetchall()
                db.close()
                return json_response(self, {"categories": [{"name": r["category"], "count": r["count"]} for r in rows]})

            elif path.startswith("/foods/search"):
                q = params.get("q", [""])[0]
                limit = min(int(params.get("limit", [20])[0]), 100)
                db = get_db()
                if q:
                    rows = db.execute(
                        """SELECT id, name, brand, category, nutrition, portion, unit, notes
                           FROM foods WHERE user_id=1 AND deleted_at IS NULL 
                           AND (name LIKE ? OR category LIKE ? OR brand LIKE ?)
                           ORDER BY usage_count DESC, name ASC LIMIT ?""",
                        (f"%{q}%", f"%{q}%", f"%{q}%", limit)
                    ).fetchall()
                else:
                    rows = db.execute(
                        """SELECT id, name, brand, category, nutrition, portion, unit, notes
                           FROM foods WHERE user_id=1 AND deleted_at IS NULL
                           ORDER BY name ASC LIMIT ?""",
                        (limit,)
                    ).fetchall()
                db.close()
                return json_response(self, {
                    "foods": [_parse_food_row(r) for r in rows],
                    "count": len(rows)
                })

            elif path.startswith("/foods/"):
                fid = int(path.split("/foods/")[1])
                db = get_db()
                row = db.execute(
                    "SELECT * FROM foods WHERE user_id=1 AND id=? AND deleted_at IS NULL",
                    (fid,)
                ).fetchone()
                db.close()
                if not row:
                    return json_response(self, {"error": "not found"}, 404)
                return json_response(self, _parse_food_row(row))

            # ── STATS ──
            elif path == "/stats/daily":
                date_str = params.get("date", [date.today().isoformat()])[0]
                db = get_db()
                row = db.execute(
                    """SELECT date, items, body_stats, water, notes 
                       FROM diary WHERE user_id=1 AND date=? AND deleted_at IS NULL""",
                    (date_str,)
                ).fetchone()
                db.close()
                if not row:
                    empty_summary = {"date": date_str, "meals": {}, "totals": {
                        "calories": 0, "protein": 0, "carbs": 0, "fat": 0,
                        "fiber": 0, "sodium": 0, "water_ml": 0
                    }}
                    act_row = get_db().execute(
                        "SELECT COALESCE(SUM(kcal), 0) AS s FROM activity_log WHERE user_id=1 AND date=? AND deleted_at IS NULL",
                        (date_str,)
                    ).fetchone()
                    empty_summary["activity_kcal"] = int(act_row["s"] or 0)
                    empty_summary["net_kcal"] = 0 - empty_summary["activity_kcal"]
                    return json_response(self, empty_summary)
                summary = _compute_daily_summary(row)
                # Add activity calories for net deficit
                act_row = get_db().execute(
                    "SELECT COALESCE(SUM(kcal), 0) AS s FROM activity_log WHERE user_id=1 AND date=? AND deleted_at IS NULL",
                    (date_str,)
                ).fetchone()
                wear_row = get_db().execute(
                    "SELECT MAX(value) AS v FROM wellness_data WHERE user_id=1 AND date=? AND metric_type='active_calories'",
                    (date_str,)
                ).fetchone()
                summary["activity_kcal"] = max(int(act_row["s"] or 0), int(wear_row["v"] or 0))
                summary["net_kcal"] = summary["totals"]["calories"] - summary["activity_kcal"]
                return json_response(self, summary)

            elif path == "/stats/weekly":
                end = date.today()
                start = end - timedelta(days=6)
                db = get_db()
                rows = db.execute(
                    """SELECT * FROM diary 
                       WHERE user_id=1 AND deleted_at IS NULL 
                       AND date >= ? AND date <= ?
                       ORDER BY date ASC""",
                    (start.isoformat(), end.isoformat())
                ).fetchall()
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
                food = None
                if food_name:
                    food = db.execute(
                        "SELECT * FROM foods WHERE user_id=1 AND deleted_at IS NULL AND name LIKE ? LIMIT 1",
                        (f"%{food_name}%",)
                    ).fetchone()
                if not food and food_id:
                    food = db.execute(
                        "SELECT * FROM foods WHERE id=? AND user_id=1 AND deleted_at IS NULL",
                        (food_id,)
                    ).fetchone()
                if not food:
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

                existing = db.execute(
                    "SELECT id, items FROM diary WHERE user_id=1 AND date=? AND deleted_at IS NULL",
                    (date_str,)
                ).fetchone()

                if existing:
                    items = json.loads(existing["items"] or "[]")
                    items.append(new_item)
                    db.execute(
                        "UPDATE diary SET items=?, updated_at=? WHERE id=?",
                        (json.dumps(items), now_ts, existing["id"])
                    )
                else:
                    items = [new_item]
                    db.execute(
                        "INSERT INTO diary (user_id, date, items, body_stats, water, notes, updated_at) VALUES (1, ?, ?, '{}', '[]', '', ?)",
                        (date_str, json.dumps(items), now_ts)
                    )

                db.execute(
                    "UPDATE foods SET usage_count = usage_count + 1, last_used_at = ? WHERE id=?",
                    (date_str, food["id"])
                )
                db.commit()
                db.close()
                return json_response(self, {
                    "ok": True,
                    "date": date_str,
                    "added": {"name": food["name"], "quantity": quantity, "meal": meal_name},
                    "total_items": len(items),
                })

            elif path == "/foods/add":
                body = parse_body(self)
                name = str(body.get("name", "")).strip()[:120]
                if not name:
                    return json_response(self, {"error": "name required"}, 400)


                nutrition = body.get("nutrition", {})
                if isinstance(nutrition, dict):
                    if "carbohydrates" in nutrition and "carbs" not in nutrition:
                        nutrition["carbs"] = nutrition["carbohydrates"]  # keep both keys
                    if "protein" in nutrition and "proteins" not in nutrition:
                        nutrition["proteins"] = nutrition["protein"]  # NutriTrade web UI expects plural
                    nutrition = json.dumps(nutrition)
                portion = float(body.get("portion", 100))
                unit = str(body.get("unit", "g"))[:10]
                category = str(body.get("category", ""))[:60] or None
                brand = str(body.get("brand", ""))[:80] or None
                notes = str(body.get("notes", ""))[:500] or None
                barcode = str(body.get("barcode", ""))[:50] or None

                db = get_db()
                db.execute(
                    """INSERT INTO foods (user_id, name, brand, category, nutrition, portion, unit, notes, barcode)
                       VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (name, brand, category, nutrition, portion, unit, notes, barcode)
                )
                db.commit()
                new_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
                row = db.execute("SELECT * FROM foods WHERE id=?", (new_id,)).fetchone()
                db.close()
                return json_response(self, {"ok": True, "food": _parse_food_row(row)})

            elif path == "/weight/log":
                body = parse_body(self)
                weight = body.get("weight")
                date_str = body.get("date", date.today().isoformat())
                unit = body.get("unit", "kg")
                notes = body.get("notes", "")

                if not weight:
                    return json_response(self, {"error": "weight required"}, 400)

                db = get_db()
                # Check existing diary entry
                existing = db.execute(
                    "SELECT id, body_stats FROM diary WHERE user_id=1 AND date=? AND deleted_at IS NULL",
                    (date_str,)
                ).fetchone()

                now = datetime.now().isoformat()
                if existing:
                    bs = json.loads(existing["body_stats"]) if existing["body_stats"] else {}
                    bs["weight"] = weight
                    bs["weight_unit"] = unit
                    db.execute(
                        "UPDATE diary SET body_stats=?, updated_at=? WHERE id=?",
                        (json.dumps(bs), now, existing["id"])
                    )
                else:
                    bs = json.dumps({"weight": weight, "weight_unit": unit})
                    db.execute(
                        """INSERT INTO diary (user_id, date, items, body_stats, water, notes, updated_at)
                           VALUES (1, ?, '[]', ?, '[]', ?, ?)""",
                        (date_str, bs, notes, now)
                    )
                db.commit()
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
                now = datetime.now().isoformat()
                db.execute(
                    """INSERT INTO activity_log (user_id, date, name, kcal, duration_min, distance, source, created_at, updated_at)
                       VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (date_str, name, kcal, duration_min, distance, source, now, now)
                )
                db.commit()
                row = db.execute("SELECT * FROM activity_log WHERE id = last_insert_rowid()").fetchone()
                db.close()
                return json_response(self, dict(row), 201)

            else:
                return json_response(self, {"error": "not found"}, 404)

        except Exception as e:
            print(f"ERROR: {e}", flush=True)
            return json_response(self, {"error": str(e)}, 500)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        try:
            if path.startswith("/diary/"):
                date_str = path.split("/diary/")[1]
                body = parse_body(self)
                food_id = body.get("food_server_id")
                meal = body.get("meal")

                if not food_id:
                    return json_response(self, {"error": "food_server_id required"}, 400)

                db = get_db()
                row = db.execute(
                    "SELECT id, items FROM diary WHERE user_id=1 AND date=? AND deleted_at IS NULL",
                    (date_str,)
                ).fetchone()

                if not row:
                    db.close()
                    return json_response(self, {"ok": True, "date": date_str, "deleted": [], "note": "no diary for date"})

                items = json.loads(row["items"] or "[]")
                original_count = len(items)
                removed = []

                if meal is not None:
                    new_items = []
                    for it in items:
                        if it.get("food_server_id") == int(food_id) and it.get("meal") == int(meal):
                            removed.append({"name": it.get("name"), "food_server_id": it.get("food_server_id"), "meal": it.get("meal")})
                        else:
                            new_items.append(it)
                    items = new_items
                else:
                    new_items = []
                    for it in items:
                        if it.get("food_server_id") == int(food_id):
                            removed.append({"name": it.get("name"), "food_server_id": it.get("food_server_id"), "meal": it.get("meal")})
                        else:
                            new_items.append(it)
                    items = new_items

                if len(items) == original_count:
                    db.close()
                    return json_response(self, {"ok": False, "error": "no matching items found", "food_server_id": food_id})

                now = datetime.now().isoformat()
                db.execute("UPDATE diary SET items=?, updated_at=? WHERE id=?", (json.dumps(items), now, row["id"]))
                db.commit()
                db.close()
                return json_response(self, {"ok": True, "date": date_str, "deleted": removed, "remaining_items": len(items)})

            return json_response(self, {"error": "not found"}, 404)
        except Exception as e:
            print(f"DELETE ERROR: {e}", flush=True)
            return json_response(self, {"error": str(e)}, 500)

    def do_PATCH(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        try:
            if path.startswith("/diary/"):
                date_str = path.split("/diary/")[1]
                body = parse_body(self)
                food_id = body.get("food_server_id")
                quantity = body.get("quantity")
                meal = body.get("meal")

                if not food_id:
                    return json_response(self, {"error": "food_server_id required"}, 400)
                if quantity is None and meal is None:
                    return json_response(self, {"error": "quantity or meal required"}, 400)

                db = get_db()
                row = db.execute(
                    "SELECT id, items FROM diary WHERE user_id=1 AND date=? AND deleted_at IS NULL",
                    (date_str,)
                ).fetchone()

                if not row:
                    db.close()
                    return json_response(self, {"error": "no diary for date"}, 404)

                items = json.loads(row["items"] or "[]")
                found = False
                updated = None

                for it in items:
                    if it.get("food_server_id") == int(food_id):
                        old_qty = it.get("quantity", 1)
                        old_meal = it.get("meal", 0)
                        if quantity is not None:
                            it["quantity"] = float(quantity)
                        if meal is not None:
                            it["meal"] = int(meal)
                        found = True
                        updated = {
                            "name": it.get("name"),
                            "food_server_id": it.get("food_server_id"),
                            "quantity": it.get("quantity"),
                            "old_quantity": old_qty,
                            "meal": it.get("meal"),
                            "old_meal": old_meal,
                        }
                        break

                if not found:
                    db.close()
                    return json_response(self, {"error": "no matching item", "food_server_id": food_id}, 404)

                now = datetime.now().isoformat()
                db.execute("UPDATE diary SET items=?, updated_at=? WHERE id=?", (json.dumps(items), now, row["id"]))
                db.commit()
                db.close()
                return json_response(self, {"ok": True, "date": date_str, "updated": updated})

            return json_response(self, {"error": "not found"}, 404)
        except Exception as e:
            print(f"PATCH ERROR: {e}", flush=True)
            return json_response(self, {"error": str(e)}, 500)



# ── Helpers ──

def _parse_diary_row(row):
    def _get(row, key, default=None):
        try:
            return row[key]
        except (KeyError, IndexError):
            return default
    return {
        "id": row["id"],
        "date": row["date"],
        "items": json.loads(row["items"] or "[]"),
        "body_stats": json.loads(row["body_stats"] or "{}"),
        "water": json.loads(row["water"] or "[]"),
        "notes": row["notes"] or "",
        "updated_at": _get(row, "updated_at"),
    }


def _parse_food_row(row):
    def _get(row, key, default=None):
        try:
            return row[key]
        except (KeyError, IndexError):
            return default
    return {
        "id": _get(row, "id"),
        "name": _get(row, "name"),
        "brand": _get(row, "brand"),
        "category": _get(row, "category"),
        "nutrition": json.loads(_get(row, "nutrition") or "{}"),
        "portion": _get(row, "portion"),
        "unit": _get(row, "unit"),
        "notes": _get(row, "notes"),
        "barcode": _get(row, "barcode"),
        "favorite": bool(_get(row, "favorite", 0)),
        "usage_count": _get(row, "usage_count", 0),
    }


MEAL_NAMES = {0: "breakfast", 1: "lunch", 2: "dinner", 3: "snacks"}

def _normalize_nutrition(nutrition):
    """Normalize nutrition keys to canonical form.
    Foods may use different key names: proteins/protein, carbohydrates/carbs, sugars/sugar.
    Returns dict with canonical keys: calories, protein, carbs, fat, fiber, sodium."""
    if not nutrition:
        return {}
    n = dict(nutrition)  # shallow copy
    # Canonical aliases
    if "proteins" in n and "protein" not in n:
        n["protein"] = n.pop("proteins")
    if "protein" in n and "proteins" not in n:
        n["proteins"] = n["protein"]  # NutriTrade web UI expects plural
    if "carbohydrates" in n and "carbs" not in n:
        n["carbs"] = n.pop("carbohydrates")
    # Also handle the reverse (carbs → carbohydrates for foods that use carbs)
    if "carbs" in n and "carbohydrates" not in n:
        n["carbohydrates"] = n["carbs"]
    # sugar → sugars (not critical for stats but keeps things clean)
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
        # NutriTrace inlines the full food object into diary items.
        # Nutrition values are per-serving (scaled to item.portion * item.quantity by NutriTrace).
        name = item.get("name", "unknown")
        qty = item.get("quantity", 1) or 1
        nutrition = _normalize_nutrition(item.get("nutrition"))

        # Map numeric meal slot to name
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

    # Round totals
    for k in totals:
        totals[k] = round(totals[k])
    for m in meals.values():
        for k in ("calories", "protein", "carbs", "fat"):
            m[k] = round(m[k])

    # Water
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
    print(f"Starting NutriTrace API on port {PORT}...")
    server = HTTPServer(("0.0.0.0", PORT), APIHandler)
    print(f"Listening on http://0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()
