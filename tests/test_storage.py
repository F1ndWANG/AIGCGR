from __future__ import annotations

from pathlib import Path

from app import storage


def test_feedback_summary_and_cache_use_temp_db(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "liferec-test.sqlite3")

    feedback_id = storage.save_feedback_event(
        request_id="req-1",
        user_id="u-test",
        item_id="poi-1",
        item_name="测试餐厅",
        item_type="restaurant",
        action="like",
        reason=None,
        tags=["清淡", "餐厅"],
        source="amap",
    )
    assert feedback_id == 1

    summary = storage.feedback_summary("u-test")
    assert summary["positive"]["items"]["测试餐厅"] == 1
    assert summary["positive"]["tags"]["清淡"] == 1
    assert summary["events"][0]["source"] == "amap"

    storage.set_cache("cache-key", "amap", {"status": "1", "pois": []}, ttl_seconds=60)
    assert storage.get_cache("cache-key") == {"status": "1", "pois": []}

    storage.save_recommendation_event(
        request_id="req-refresh",
        user_id="u-test",
        scenario="restaurant",
        message="换一个测试",
        request_payload={"message": "换一个测试", "scenario": "restaurant", "user_id": "u-test"},
        context={"weather_source": "amap"},
        recommendations=[{"id": "poi-1", "name": "测试餐厅"}],
    )
    event = storage.get_recommendation_event("req-refresh")
    assert event is not None
    assert event["request"]["message"] == "换一个测试"
    assert event["recommendations"][0]["id"] == "poi-1"

    meal_id = storage.save_meal_event(
        user_id="u-test",
        meal_name="炸鸡和奶茶",
        tags=["高油", "高糖", "蔬菜少"],
        note="晚餐",
    )
    assert meal_id == 1
    meals = storage.meal_history("u-test")
    assert meals[0]["meal_name"] == "炸鸡和奶茶"
    assert meals[0]["tags"] == ["高油", "高糖", "蔬菜少"]
    assert storage.recent_meal_tags("u-test") == ["高油", "高糖", "蔬菜少"]

    wellness_id = storage.save_wellness_event(
        user_id="u-test",
        tags=["睡眠不足", "压力高", "压力高"],
        sleep_hours=5.5,
        exercise_minutes=10,
        stress_level=4,
        mood="疲惫",
    )
    assert wellness_id == 1
    wellness = storage.wellness_history("u-test")
    assert wellness[0]["tags"] == ["睡眠不足", "压力高"]
    assert wellness[0]["sleep_hours"] == 5.5
    assert storage.recent_wellness_tags("u-test") == ["睡眠不足", "压力高"]

    preferences = storage.save_user_preferences(
        user_id="u-test",
        default_location="南京江宁",
        default_budget=50,
        taste=["清淡", "清淡", "高蛋白"],
        avoid=["油炸"],
        allergies=["花生"],
        health_goals=["控糖"],
        travel_style=["轻松"],
    )
    assert preferences["taste"] == ["清淡", "高蛋白"]
    assert storage.user_preferences("u-test")["default_budget"] == 50
    assert storage.storage_status()["user_preferences"] == 1
    assert storage.storage_status()["wellness_events"] == 1

    plan = storage.save_plan_item(
        user_id="u-test",
        request_id="req-refresh",
        item_id="poi-1",
        item_name="测试餐厅",
        item_type="restaurant",
        title="今晚吃测试餐厅",
        tags=["清淡", "餐厅"],
        source="amap",
        note="来自真实 POI",
    )
    assert plan["status"] == "active"
    assert storage.plan_items("u-test")[0]["title"] == "今晚吃测试餐厅"
    duplicate = storage.save_plan_item(
        user_id="u-test",
        request_id="req-refresh",
        item_id="poi-1",
        item_name="测试餐厅",
        item_type="restaurant",
        title="重复计划",
        tags=["清淡"],
        source="amap",
    )
    assert duplicate["id"] == plan["id"]
    updated = storage.update_plan_item_status(plan_id=plan["id"], user_id="u-test", status="done")
    assert updated is not None
    assert updated["status"] == "done"
    assert storage.plan_items("u-test", status="active") == []
    assert storage.storage_status()["plan_items"] == 1


def test_expired_cache_returns_none(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "liferec-test.sqlite3")

    storage.set_cache("expired-key", "amap", {"ok": True}, ttl_seconds=-1)
    assert storage.get_cache("expired-key") is None
