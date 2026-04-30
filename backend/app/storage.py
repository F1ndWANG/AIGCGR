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
        bucket = "positive" if action in {"like", "save", "plan"} else "negative"
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
    return {
        "database": str(DB_PATH),
        "recommendation_events": recommendation_count,
        "feedback_events": feedback_count,
        "cache_entries": cache_count,
        "meal_events": meal_count,
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


def _empty_profile(user_id: str) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "positive": {"items": {}, "tags": {}},
        "negative": {"items": {}, "tags": {}},
        "events": [],
    }
