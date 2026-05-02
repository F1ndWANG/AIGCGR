from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.models import RecommendationItem, ScoreBreakdown
from app import recommender, storage
from app.recommender import _apply_feedback_profile, _exclude_items


def test_feedback_profile_adjusts_scores() -> None:
    item = RecommendationItem(
        id="poi-1",
        name="测试餐厅",
        type="restaurant",
        score=60,
        tags=["清淡", "餐厅"],
        reasons=["基础推荐理由"],
        meta={"source": "amap"},
        score_breakdown=ScoreBreakdown(preference=0.5, health=0.5, budget=0.5, distance=0.5, context=0.5),
    )
    profile = {
        "positive": {"items": {"测试餐厅": 1}, "tags": {"清淡": 2}},
        "negative": {"items": {}, "tags": {}},
    }

    adjusted = _apply_feedback_profile([item], profile)
    assert adjusted[0].score > 60
    assert adjusted[0].meta["feedback_adjustment"] > 0
    assert "反馈" in adjusted[0].reasons[-1]


def test_exclude_items_filters_previous_results() -> None:
    first = RecommendationItem(
        id="poi-1",
        name="第一家",
        type="restaurant",
        score=80,
        tags=[],
        reasons=[],
        meta={},
        score_breakdown=ScoreBreakdown(preference=0.5, health=0.5, budget=0.5, distance=0.5, context=0.5),
    )
    second = RecommendationItem(
        id="poi-2",
        name="第二家",
        type="restaurant",
        score=70,
        tags=[],
        reasons=[],
        meta={},
        score_breakdown=ScoreBreakdown(preference=0.5, health=0.5, budget=0.5, distance=0.5, context=0.5),
    )

    filtered = _exclude_items([first, second], item_ids=["poi-1"], item_names=[])
    assert [item.id for item in filtered] == ["poi-2"]


def test_recommend_uses_runtime_meal_tags_when_request_is_empty(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "liferec-test.sqlite3")
    monkeypatch.setattr(recommender, "settings", SimpleNamespace(strict_real_data=True, amap_api_key=None))

    storage.save_meal_event(
        user_id="u-meal",
        meal_name="炸鸡",
        tags=["高油"],
    )

    response = recommender.recommend(
        message="今天想吃健康一点",
        scenario="restaurant",
        user_id="u-meal",
        recent_meal_tags=[],
    )

    assert response.context["recent_meal_tags_source"] == "runtime-storage"
    assert response.context["recent_meal_tag_count"] == 1
    assert "高油" in response.health_summary


def test_recommend_uses_runtime_wellness_tags_when_request_is_empty(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "liferec-test.sqlite3")
    monkeypatch.setattr(recommender, "settings", SimpleNamespace(strict_real_data=True, amap_api_key=None))

    storage.save_wellness_event(
        user_id="u-wellness",
        tags=["睡眠不足", "压力高"],
        sleep_hours=5,
        stress_level=4,
    )

    response = recommender.recommend(
        message="今天想吃舒服一点",
        scenario="restaurant",
        user_id="u-wellness",
        recent_meal_tags=[],
        recent_wellness_tags=[],
    )

    assert response.context["recent_wellness_tags_source"] == "runtime-storage"
    assert response.context["recent_wellness_tag_count"] == 2
    assert "睡眠不足" in response.health_summary
    assert "压力高" in response.health_summary


def test_recommend_uses_stored_preferences_when_request_is_empty(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "liferec-test.sqlite3")
    monkeypatch.setattr(recommender, "settings", SimpleNamespace(strict_real_data=True, amap_api_key=None))

    storage.save_user_preferences(
        user_id="u-pref",
        default_location="南京江宁",
        default_budget=42,
        taste=["清淡"],
        avoid=["油炸"],
        allergies=[],
        health_goals=["减脂"],
        travel_style=["轻松"],
    )

    response = recommender.recommend(
        message="今天晚上吃什么",
        scenario="restaurant",
        user_id="u-pref",
    )

    assert response.context["preferences_source"] == "runtime-storage"
    assert response.context["stored_preference_count"] == 6
    assert "地点：南京江宁" in response.intent_summary
    assert "预算：42 元" in response.intent_summary
