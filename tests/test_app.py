from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.aigc import _message_text, _parse_product_json
from app import storage
from app.main import app


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "storage" in payload


def test_cors_allows_configured_local_frontend_origin() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_user_context_endpoint_aggregates_runtime_data(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "liferec-test.sqlite3")

    with TestClient(app) as client:
        meal_response = client.post(
            "/api/user/meals",
            json={
                "user_id": "u-context",
                "meal_name": "炸鸡",
                "tags": ["高油", "蔬菜少"],
            },
        )
        wellness_response = client.post(
            "/api/user/wellness",
            json={
                "user_id": "u-context",
                "tags": ["睡眠不足", "压力高"],
                "sleep_hours": 5.5,
                "exercise_minutes": 10,
                "stress_level": 4,
            },
        )
        feedback_response = client.post(
            "/api/feedback",
            json={
                "user_id": "u-context",
                "item_id": "poi-1",
                "item_name": "测试餐厅",
                "item_type": "restaurant",
                "action": "like",
                "tags": ["清淡"],
                "source": "amap",
            },
        )
        preferences_response = client.put(
            "/api/user/preferences",
            json={
                "user_id": "u-context",
                "default_location": "南京江宁",
                "default_budget": 45,
                "taste": ["清淡"],
                "avoid": ["油炸"],
                "allergies": ["花生"],
                "health_goals": ["减脂"],
                "travel_style": ["轻松"],
            },
        )
        plan_response = client.post(
            "/api/user/plans",
            json={
                "user_id": "u-context",
                "request_id": "req-context",
                "item_id": "poi-1",
                "item_name": "测试餐厅",
                "item_type": "restaurant",
                "title": "今晚去测试餐厅",
                "tags": ["清淡"],
                "source": "amap",
            },
        )
        context_response = client.get("/api/user/context?user_id=u-context&limit=10")

    assert meal_response.status_code == 200
    assert wellness_response.status_code == 200
    assert feedback_response.status_code == 200
    assert preferences_response.status_code == 200
    assert plan_response.status_code == 200
    assert context_response.status_code == 200
    payload = context_response.json()
    assert payload["recent_meal_tags"] == ["高油", "蔬菜少"]
    assert payload["recent_wellness_tags"] == ["睡眠不足", "压力高"]
    assert payload["meals"][0]["meal_name"] == "炸鸡"
    assert payload["wellness"][0]["sleep_hours"] == 5.5
    assert payload["feedback"]["positive"]["items"]["测试餐厅"] == 1
    assert payload["preferences"]["default_location"] == "南京江宁"
    assert payload["preferences"]["taste"] == ["清淡"]
    assert payload["plans"][0]["title"] == "今晚去测试餐厅"
    assert payload["plans"][0]["status"] == "active"
    assert payload["storage"]["meal_events"] == 1
    assert payload["storage"]["wellness_events"] == 1
    assert payload["storage"]["user_preferences"] == 1
    assert payload["storage"]["plan_items"] == 1
    assert payload["context_sources"]["meals"] == "runtime.sqlite.meal_events"
    assert payload["context_sources"]["wellness"] == "runtime.sqlite.wellness_events"
    assert payload["context_sources"]["preferences"] == "runtime.sqlite.user_preferences"
    assert payload["context_sources"]["plans"] == "runtime.sqlite.plan_items"


def test_plan_status_api_updates_active_list(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "liferec-test.sqlite3")

    with TestClient(app) as client:
        created = client.post(
            "/api/user/plans",
            json={
                "user_id": "u-plan-api",
                "item_id": "poi-1",
                "item_name": "测试餐厅",
                "item_type": "restaurant",
                "title": "今晚去测试餐厅",
                "tags": ["清淡"],
                "source": "amap",
            },
        )
        plan_id = created.json()["id"]
        scheduled = client.patch(
            f"/api/user/plans/{plan_id}",
            json={"user_id": "u-plan-api", "scheduled_for": "2030-01-02T03:04:00+00:00"},
        )
        updated = client.patch(
            f"/api/user/plans/{plan_id}",
            json={"user_id": "u-plan-api", "status": "done"},
        )
        active = client.get("/api/user/plans?user_id=u-plan-api&status=active")
        done = client.get("/api/user/plans?user_id=u-plan-api&status=done")
        exported = client.get("/api/user/plans/export?user_id=u-plan-api")
        exported_ics = client.get("/api/user/plans/export.ics?user_id=u-plan-api&status=done")

    assert created.status_code == 200
    assert scheduled.status_code == 200
    assert scheduled.json()["scheduled_for"] == "2030-01-02T03:04:00+00:00"
    assert updated.status_code == 200
    assert updated.json()["status"] == "done"
    assert updated.json()["scheduled_for"] == "2030-01-02T03:04:00+00:00"
    assert active.status_code == 200
    assert active.json()["plans"] == []
    assert done.status_code == 200
    assert done.json()["plans"][0]["id"] == plan_id
    assert exported.status_code == 200
    export_payload = exported.json()
    assert export_payload["summary"]["active"] == 0
    assert export_payload["summary"]["done"] == 1
    assert export_payload["summary"]["total"] == 1
    assert export_payload["done"][0]["id"] == plan_id
    assert exported_ics.status_code == 200
    assert "text/calendar" in exported_ics.headers["content-type"]
    assert "BEGIN:VCALENDAR" in exported_ics.text
    assert "BEGIN:VEVENT" in exported_ics.text
    assert "DTSTART:20300102T030400Z" in exported_ics.text
    assert "今晚去测试餐厅" in exported_ics.text


def test_recommendation_history_api_uses_runtime_events(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "liferec-test.sqlite3")
    storage.save_recommendation_event(
        request_id="req-history-1",
        user_id="u-history",
        scenario="restaurant",
        message="Need a light dinner near campus",
        request_payload={"message": "Need a light dinner near campus", "scenario": "restaurant"},
        context={"location": "campus", "radius_km": 3, "dynamic_location_enabled": False},
        recommendations=[
            {
                "id": "poi-1",
                "name": "Real Place",
                "type": "restaurant",
                "score": 0.91,
                "tags": ["light"],
                "meta": {"source": "amap"},
            }
        ],
    )

    with TestClient(app) as client:
        history = client.get("/api/user/recommendations?user_id=u-history&limit=5")
        context = client.get("/api/user/context?user_id=u-history&limit=5")

    assert history.status_code == 200
    payload = history.json()
    assert payload["user_id"] == "u-history"
    assert payload["recommendations"][0]["request_id"] == "req-history-1"
    assert payload["recommendations"][0]["item_count"] == 1
    assert payload["recommendations"][0]["top_items"][0]["name"] == "Real Place"
    assert payload["recommendations"][0]["top_items"][0]["source"] == "amap"
    assert context.status_code == 200
    assert context.json()["recent_recommendations"][0]["request_id"] == "req-history-1"


def test_daily_brief_api_aggregates_runtime_context(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "liferec-test.sqlite3")

    with TestClient(app) as client:
        client.post(
            "/api/user/meals",
            json={"user_id": "u-brief", "meal_name": "Salad", "tags": ["high-oil"]},
        )
        client.post(
            "/api/user/wellness",
            json={"user_id": "u-brief", "tags": ["stress-high"], "stress_level": 4},
        )
        client.put(
            "/api/user/preferences",
            json={"user_id": "u-brief", "default_location": "Nanjing", "default_budget": 50},
        )
        response = client.get("/api/user/daily-brief?user_id=u-brief&limit=10")

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == "u-brief"
    assert payload["provider"] in {"context-generator", "unavailable", "llm"}
    assert payload["summary"]
    assert payload["context_sources"]["meals"] == "runtime.sqlite.meal_events"
    assert payload["context_sources"]["recommendations"] == "runtime.sqlite.recommendation_events"


def test_user_runtime_context_is_isolated_by_user_id(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "liferec-test.sqlite3")

    with TestClient(app) as client:
        client.post(
            "/api/user/meals",
            json={"user_id": "u-alpha", "meal_name": "沙拉", "tags": ["清淡"]},
        )
        client.post(
            "/api/user/wellness",
            json={"user_id": "u-alpha", "tags": ["睡眠不足"], "sleep_hours": 5},
        )
        client.put(
            "/api/user/preferences",
            json={"user_id": "u-alpha", "default_location": "南京", "taste": ["清淡"]},
        )
        client.post(
            "/api/user/plans",
            json={
                "user_id": "u-alpha",
                "item_id": "alpha-plan",
                "item_name": "Alpha 餐厅",
                "item_type": "restaurant",
                "tags": ["清淡"],
                "source": "amap",
            },
        )
        client.post(
            "/api/user/meals",
            json={"user_id": "u-beta", "meal_name": "炸鸡", "tags": ["高油"]},
        )

        alpha = client.get("/api/user/context?user_id=u-alpha&limit=10").json()
        beta = client.get("/api/user/context?user_id=u-beta&limit=10").json()

    assert alpha["recent_meal_tags"] == ["清淡"]
    assert alpha["recent_wellness_tags"] == ["睡眠不足"]
    assert alpha["preferences"]["default_location"] == "南京"
    assert alpha["plans"][0]["item_name"] == "Alpha 餐厅"
    assert beta["recent_meal_tags"] == ["高油"]
    assert beta["recent_wellness_tags"] == []
    assert beta["preferences"]["default_location"] is None
    assert beta["plans"] == []


def test_aigc_product_parser_accepts_reasoning_content_and_embedded_json() -> None:
    text = _message_text(
        {
            "content": "",
            "reasoning_content": '说明文字后输出 [{"name":"无糖酸奶","category":"健康食材","price":42,"tags":["低糖"],"reason":"减少糖摄入","purchase_hint":"看配料表"}]',
        }
    )
    products = _parse_product_json(text)

    assert products[0]["name"] == "无糖酸奶"


def test_aigc_product_parser_keeps_complete_items_from_truncated_array() -> None:
    products = _parse_product_json(
        """
        [
          {"name":"即食鸡胸肉","category":"健康食材","price":59,"tags":["高蛋白"],"reason":"补充蛋白","purchase_hint":"看钠含量"},
          {"name":"无糖酸奶","category":"健康食材","price":42,"tags":["低糖"],"reason":"减少糖摄入","purchase_hint":"看配料表"},
          {"name":"未完成"
        """
    )

    assert [item["name"] for item in products] == ["即食鸡胸肉", "无糖酸奶"]
