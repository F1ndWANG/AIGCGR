from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
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
                context_json TEXT NOT NULL,
                recommendations_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
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


def save_recommendation_event(
    request_id: str,
    user_id: str,
    scenario: str,
    message: str,
    context: dict[str, Any],
    recommendations: list[dict[str, Any]],
) -> None:
    init_storage()
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO recommendation_events
            (request_id, user_id, scenario, message, context_json, recommendations_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                user_id,
                scenario,
                message,
                json.dumps(context, ensure_ascii=False),
                json.dumps(recommendations, ensure_ascii=False),
                _now(),
            ),
        )


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


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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


def _empty_profile(user_id: str) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "positive": {"items": {}, "tags": {}},
        "negative": {"items": {}, "tags": {}},
        "events": [],
    }
