from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = ROOT / "runtime"
DB_PATH = RUNTIME_DIR / "liferec.sqlite3"


def init_storage() -> None:
    RUNTIME_DIR.mkdir(exist_ok=True)
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recommendation_events (
                request_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                scenario TEXT NOT NULL,
                message TEXT NOT NULL,
                request_json TEXT NOT NULL DEFAULT '{}',
                context_json TEXT NOT NULL,
                recommendations_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        _ensure_column(conn, "recommendation_events", "request_json", "TEXT NOT NULL DEFAULT '{}'")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT,
                user_id TEXT NOT NULL,
                item_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                item_type TEXT NOT NULL,
                action TEXT NOT NULL,
                reason TEXT,
                tags_json TEXT NOT NULL,
                source TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_cache (
                cache_key TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meal_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                meal_name TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                note TEXT,
                meal_time TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT PRIMARY KEY,
                default_location TEXT,
                default_budget REAL,
                taste_json TEXT NOT NULL DEFAULT '[]',
                avoid_json TEXT NOT NULL DEFAULT '[]',
                allergies_json TEXT NOT NULL DEFAULT '[]',
                health_goals_json TEXT NOT NULL DEFAULT '[]',
                travel_style_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wellness_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                sleep_hours REAL,
                exercise_minutes INTEGER,
                stress_level INTEGER,
                mood TEXT,
                note TEXT,
                event_time TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS plan_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                request_id TEXT,
                item_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                item_type TEXT NOT NULL,
                title TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                source TEXT,
                note TEXT,
                scheduled_for TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


def save_recommendation_event(
    request_id: str,
    user_id: str,
    scenario: str,
    message: str,
    request_payload: dict[str, Any],
    context: dict[str, Any],
    recommendations: list[dict[str, Any]],
) -> None:
    init_storage()
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO recommendation_events
            (request_id, user_id, scenario, message, request_json, context_json, recommendations_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                user_id,
                scenario,
                message,
                json.dumps(request_payload, ensure_ascii=False),
                json.dumps(context, ensure_ascii=False),
                json.dumps(recommendations, ensure_ascii=False),
                _now(),
            ),
        )


def get_recommendation_event(request_id: str) -> dict[str, Any] | None:
    init_storage()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT request_id, user_id, scenario, message, request_json, context_json, recommendations_json, created_at
            FROM recommendation_events
            WHERE request_id = ?
            """,
            (request_id,),
        ).fetchone()
    if not row:
        return None
    return {
        "request_id": row["request_id"],
        "user_id": row["user_id"],
        "scenario": row["scenario"],
        "message": row["message"],
        "request": _loads_dict(row["request_json"]),
        "context": _loads_dict(row["context_json"]),
        "recommendations": _loads_list_of_dicts(row["recommendations_json"]),
        "created_at": row["created_at"],
    }


def recommendation_history(user_id: str, limit: int = 20) -> list[dict[str, Any]]:
    init_storage()
    safe_limit = max(1, min(limit, 100))
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT request_id, user_id, scenario, message, context_json, recommendations_json, created_at
            FROM recommendation_events
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, safe_limit),
        ).fetchall()

    history: list[dict[str, Any]] = []
    for row in rows:
        recommendations = _loads_list_of_dicts(row["recommendations_json"])
        history.append(
            {
                "request_id": row["request_id"],
                "scenario": row["scenario"],
                "message": row["message"],
                "created_at": row["created_at"],
                "context": _loads_dict(row["context_json"]),
                "item_count": len(recommendations),
                "top_items": [_recommendation_top_item(item) for item in recommendations[:3]],
            }
        )
    return history


def save_feedback_event(
    request_id: str | None,
    user_id: str,
    item_id: str,
    item_name: str,
    item_type: str,
    action: str,
    reason: str | None,
    tags: list[str],
    source: str | None,
) -> int:
    init_storage()
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO feedback_events
            (request_id, user_id, item_id, item_name, item_type, action, reason, tags_json, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                user_id,
                item_id,
                item_name,
                item_type,
                action,
                reason,
                json.dumps(tags, ensure_ascii=False),
                source,
                _now(),
            ),
        )
        return int(cursor.lastrowid)


def feedback_summary(user_id: str, limit: int = 200) -> dict[str, Any]:
    init_storage()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT item_id, item_name, item_type, action, tags_json, source, created_at
            FROM feedback_events
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()

    profile = _empty_profile(user_id)
    for row in rows:
        action = str(row["action"])
        tags = _loads_list(row["tags_json"])
        bucket = "positive" if action in {"like", "save", "plan", "done"} else "negative"
        profile[bucket]["items"][row["item_name"]] = profile[bucket]["items"].get(row["item_name"], 0) + 1
        for tag in tags:
            profile[bucket]["tags"][tag] = profile[bucket]["tags"].get(tag, 0) + 1
        profile["events"].append(
            {
                "item_id": row["item_id"],
                "item_name": row["item_name"],
                "item_type": row["item_type"],
                "action": action,
                "tags": tags,
                "source": row["source"],
                "created_at": row["created_at"],
            }
        )
    return profile


def save_meal_event(
    user_id: str,
    meal_name: str,
    tags: list[str],
    note: str | None = None,
    meal_time: str | None = None,
) -> int:
    init_storage()
    normalized_tags = [tag.strip() for tag in tags if tag and tag.strip()]
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO meal_events
            (user_id, meal_name, tags_json, note, meal_time, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                meal_name.strip(),
                json.dumps(normalized_tags, ensure_ascii=False),
                note,
                meal_time,
                _now(),
            ),
        )
        return int(cursor.lastrowid)


def meal_history(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    init_storage()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, meal_name, tags_json, note, meal_time, created_at
            FROM meal_events
            WHERE user_id = ?
            ORDER BY COALESCE(meal_time, created_at) DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "user_id": row["user_id"],
            "meal_name": row["meal_name"],
            "tags": _loads_list(row["tags_json"]),
            "note": row["note"],
            "meal_time": row["meal_time"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def recent_meal_tags(user_id: str, limit: int = 20) -> list[str]:
    tags: list[str] = []
    for event in meal_history(user_id=user_id, limit=limit):
        tags.extend(event["tags"])
    seen: set[str] = set()
    deduped: list[str] = []
    for tag in tags:
        if tag not in seen:
            deduped.append(tag)
            seen.add(tag)
    return deduped


def save_wellness_event(
    user_id: str,
    tags: list[str],
    sleep_hours: float | None = None,
    exercise_minutes: int | None = None,
    stress_level: int | None = None,
    mood: str | None = None,
    note: str | None = None,
    event_time: str | None = None,
) -> int:
    init_storage()
    normalized_tags = _normalize_tags(tags)
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO wellness_events
            (user_id, tags_json, sleep_hours, exercise_minutes, stress_level, mood, note, event_time, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                json.dumps(normalized_tags, ensure_ascii=False),
                sleep_hours,
                exercise_minutes,
                stress_level,
                _clean_text(mood),
                _clean_text(note),
                _clean_text(event_time),
                _now(),
            ),
        )
        return int(cursor.lastrowid)


def wellness_history(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    init_storage()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, tags_json, sleep_hours, exercise_minutes, stress_level,
                   mood, note, event_time, created_at
            FROM wellness_events
            WHERE user_id = ?
            ORDER BY COALESCE(event_time, created_at) DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "user_id": row["user_id"],
            "tags": _loads_list(row["tags_json"]),
            "sleep_hours": row["sleep_hours"],
            "exercise_minutes": row["exercise_minutes"],
            "stress_level": row["stress_level"],
            "mood": row["mood"],
            "note": row["note"],
            "event_time": row["event_time"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def recent_wellness_tags(user_id: str, limit: int = 20) -> list[str]:
    tags: list[str] = []
    for event in wellness_history(user_id=user_id, limit=limit):
        tags.extend(event["tags"])
    seen: set[str] = set()
    deduped: list[str] = []
    for tag in tags:
        if tag not in seen:
            deduped.append(tag)
            seen.add(tag)
    return deduped


def save_user_preferences(
    user_id: str,
    default_location: str | None,
    default_budget: float | None,
    taste: list[str],
    avoid: list[str],
    allergies: list[str],
    health_goals: list[str],
    travel_style: list[str],
) -> dict[str, Any]:
    init_storage()
    existing = user_preferences(user_id)
    created_at = existing.get("created_at") or _now()
    updated_at = _now()
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO user_preferences
            (user_id, default_location, default_budget, taste_json, avoid_json, allergies_json,
             health_goals_json, travel_style_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                _clean_text(default_location),
                default_budget,
                json.dumps(_normalize_tags(taste), ensure_ascii=False),
                json.dumps(_normalize_tags(avoid), ensure_ascii=False),
                json.dumps(_normalize_tags(allergies), ensure_ascii=False),
                json.dumps(_normalize_tags(health_goals), ensure_ascii=False),
                json.dumps(_normalize_tags(travel_style), ensure_ascii=False),
                created_at,
                updated_at,
            ),
        )
    return user_preferences(user_id)


def user_preferences(user_id: str) -> dict[str, Any]:
    init_storage()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT user_id, default_location, default_budget, taste_json, avoid_json,
                   allergies_json, health_goals_json, travel_style_json, updated_at, created_at
            FROM user_preferences
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    if not row:
        return _empty_preferences(user_id)
    return {
        "user_id": row["user_id"],
        "default_location": row["default_location"],
        "default_budget": row["default_budget"],
        "taste": _loads_list(row["taste_json"]),
        "avoid": _loads_list(row["avoid_json"]),
        "allergies": _loads_list(row["allergies_json"]),
        "health_goals": _loads_list(row["health_goals_json"]),
        "travel_style": _loads_list(row["travel_style_json"]),
        "updated_at": row["updated_at"],
        "created_at": row["created_at"],
    }


def save_plan_item(
    user_id: str,
    request_id: str | None,
    item_id: str,
    item_name: str,
    item_type: str,
    title: str | None,
    tags: list[str],
    source: str | None,
    note: str | None = None,
    scheduled_for: str | None = None,
) -> dict[str, Any]:
    init_storage()
    normalized_title = _clean_text(title) or item_name.strip()
    normalized_tags = _normalize_tags(tags)
    now = _now()
    with _connect() as conn:
        existing = conn.execute(
            """
            SELECT id, user_id, request_id, item_id, item_name, item_type, title, tags_json,
                   source, note, scheduled_for, status, created_at, updated_at
            FROM plan_items
            WHERE user_id = ? AND item_id = ? AND status = 'active'
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id, item_id),
        ).fetchone()
        if existing:
            return _plan_row_to_dict(existing)

        cursor = conn.execute(
            """
            INSERT INTO plan_items
            (user_id, request_id, item_id, item_name, item_type, title, tags_json, source,
             note, scheduled_for, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
            """,
            (
                user_id,
                request_id,
                item_id,
                item_name.strip(),
                item_type,
                normalized_title,
                json.dumps(normalized_tags, ensure_ascii=False),
                source,
                _clean_text(note),
                _clean_text(scheduled_for),
                now,
                now,
            ),
        )
        plan_id = int(cursor.lastrowid)
    plan = get_plan_item(plan_id=plan_id, user_id=user_id)
    if plan is None:
        raise RuntimeError("Plan item was not persisted")
    return plan


def get_plan_item(plan_id: int, user_id: str) -> dict[str, Any] | None:
    init_storage()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT id, user_id, request_id, item_id, item_name, item_type, title, tags_json,
                   source, note, scheduled_for, status, created_at, updated_at
            FROM plan_items
            WHERE id = ? AND user_id = ?
            """,
            (plan_id, user_id),
        ).fetchone()
    return _plan_row_to_dict(row) if row else None


def plan_items(user_id: str, status: str | None = "active", limit: int = 50) -> list[dict[str, Any]]:
    init_storage()
    safe_limit = max(1, min(limit, 200))
    with _connect() as conn:
        if status:
            rows = conn.execute(
                """
                SELECT id, user_id, request_id, item_id, item_name, item_type, title, tags_json,
                       source, note, scheduled_for, status, created_at, updated_at
                FROM plan_items
                WHERE user_id = ? AND status = ?
                ORDER BY updated_at DESC, id DESC
                LIMIT ?
                """,
                (user_id, status, safe_limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, user_id, request_id, item_id, item_name, item_type, title, tags_json,
                       source, note, scheduled_for, status, created_at, updated_at
                FROM plan_items
                WHERE user_id = ?
                ORDER BY updated_at DESC, id DESC
                LIMIT ?
                """,
                (user_id, safe_limit),
            ).fetchall()
    return [_plan_row_to_dict(row) for row in rows]


def update_plan_item(plan_id: int, user_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    init_storage()
    allowed_fields = {"status", "title", "note", "scheduled_for"}
    assignments: list[str] = []
    params: list[Any] = []

    if "status" in updates and updates["status"] is not None:
        assignments.append("status = ?")
        params.append(updates["status"])
    if "title" in updates:
        cleaned_title = _clean_text(updates["title"])
        if cleaned_title:
            assignments.append("title = ?")
            params.append(cleaned_title)
    if "note" in updates:
        assignments.append("note = ?")
        params.append(_clean_text(updates["note"]))
    if "scheduled_for" in updates:
        assignments.append("scheduled_for = ?")
        params.append(_clean_text(updates["scheduled_for"]))

    ignored_fields = set(updates) - allowed_fields
    if ignored_fields:
        raise ValueError(f"Unsupported plan update fields: {', '.join(sorted(ignored_fields))}")
    if not assignments:
        return get_plan_item(plan_id=plan_id, user_id=user_id)

    updated_at = _now()
    assignments.append("updated_at = ?")
    params.extend([updated_at, plan_id, user_id])
    with _connect() as conn:
        cursor = conn.execute(
            f"""
            UPDATE plan_items
            SET {", ".join(assignments)}
            WHERE id = ? AND user_id = ?
            """,
            params,
        )
        if cursor.rowcount == 0:
            return None
    return get_plan_item(plan_id=plan_id, user_id=user_id)


def update_plan_item_status(plan_id: int, user_id: str, status: str) -> dict[str, Any] | None:
    return update_plan_item(plan_id=plan_id, user_id=user_id, updates={"status": status})


def get_cache(cache_key: str) -> dict[str, Any] | None:
    init_storage()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT payload_json, expires_at
            FROM api_cache
            WHERE cache_key = ?
            """,
            (cache_key,),
        ).fetchone()
    if not row:
        return None
    try:
        expires_at = datetime.fromisoformat(row["expires_at"])
    except ValueError:
        return None
    if expires_at <= datetime.now(timezone.utc):
        return None
    try:
        payload = json.loads(row["payload_json"])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def set_cache(cache_key: str, provider: str, payload: dict[str, Any], ttl_seconds: int) -> None:
    init_storage()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO api_cache
            (cache_key, provider, payload_json, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                cache_key,
                provider,
                json.dumps(payload, ensure_ascii=False),
                expires_at.isoformat(),
                _now(),
            ),
        )


def storage_status() -> dict[str, Any]:
    init_storage()
    with _connect() as conn:
        recommendation_count = conn.execute("SELECT COUNT(*) FROM recommendation_events").fetchone()[0]
        feedback_count = conn.execute("SELECT COUNT(*) FROM feedback_events").fetchone()[0]
        cache_count = conn.execute("SELECT COUNT(*) FROM api_cache").fetchone()[0]
        meal_count = conn.execute("SELECT COUNT(*) FROM meal_events").fetchone()[0]
        preference_count = conn.execute("SELECT COUNT(*) FROM user_preferences").fetchone()[0]
        wellness_count = conn.execute("SELECT COUNT(*) FROM wellness_events").fetchone()[0]
        plan_count = conn.execute("SELECT COUNT(*) FROM plan_items").fetchone()[0]
    return {
        "database": str(DB_PATH),
        "recommendation_events": recommendation_count,
        "feedback_events": feedback_count,
        "cache_entries": cache_count,
        "meal_events": meal_count,
        "user_preferences": preference_count,
        "wellness_events": wellness_count,
        "plan_items": plan_count,
    }


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _loads_list(value: str) -> list[str]:
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [str(item) for item in data]


def _normalize_tags(values: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for value in values:
        item = value.strip()
        if item and item not in seen:
            normalized.append(item)
            seen.add(item)
    return normalized


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _loads_dict(value: str) -> dict[str, Any]:
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _loads_list_of_dicts(value: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _recommendation_top_item(item: dict[str, Any]) -> dict[str, Any]:
    meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
    return {
        "id": str(item.get("id") or ""),
        "name": str(item.get("name") or ""),
        "type": str(item.get("type") or ""),
        "score": item.get("score") if isinstance(item.get("score"), (int, float)) else None,
        "tags": [str(tag) for tag in item.get("tags", []) if tag is not None] if isinstance(item.get("tags"), list) else [],
        "source": str(meta.get("source") or meta.get("provider")) if meta.get("source") or meta.get("provider") else None,
    }


def _plan_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "request_id": row["request_id"],
        "item_id": row["item_id"],
        "item_name": row["item_name"],
        "item_type": row["item_type"],
        "title": row["title"],
        "tags": _loads_list(row["tags_json"]),
        "source": row["source"],
        "note": row["note"],
        "scheduled_for": row["scheduled_for"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _empty_profile(user_id: str) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "positive": {"items": {}, "tags": {}},
        "negative": {"items": {}, "tags": {}},
        "events": [],
    }


def _empty_preferences(user_id: str) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "default_location": None,
        "default_budget": None,
        "taste": [],
        "avoid": [],
        "allergies": [],
        "health_goals": [],
        "travel_style": [],
        "updated_at": None,
        "created_at": None,
    }
