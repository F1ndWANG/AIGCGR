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


def test_expired_cache_returns_none(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "liferec-test.sqlite3")

    storage.set_cache("expired-key", "amap", {"ok": True}, ttl_seconds=-1)
    assert storage.get_cache("expired-key") is None
