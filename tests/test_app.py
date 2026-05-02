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
        updated = client.patch(
            f"/api/user/plans/{plan_id}",
            json={"user_id": "u-plan-api", "status": "done"},
        )
        active = client.get("/api/user/plans?user_id=u-plan-api&status=active")
        done = client.get("/api/user/plans?user_id=u-plan-api&status=done")

    assert created.status_code == 200
    assert updated.status_code == 200
    assert updated.json()["status"] == "done"
    assert active.status_code == 200
    assert active.json()["plans"] == []
    assert done.status_code == 200
    assert done.json()["plans"][0]["id"] == plan_id


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
