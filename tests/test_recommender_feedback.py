from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.models import RecommendationItem, ScoreBreakdown
from app import recommender, storage
from app.recommender import _apply_feedback_profile, _exclude_items, _item as build_recommendation_item


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


def test_recommendation_trace_exposes_sources_evidence_and_penalties() -> None:
    item = build_recommendation_item(
        id="poi-trace",
        name="Trace Cafe",
        item_type="restaurant",
        score=72,
        tags=["light", "restaurant"],
        reasons=["trace test"],
        meta={"source": "amap", "data_type": "real-poi", "distance_km": 8},
        breakdown=(0.7, 0.8, 0.4, 0.2, 0.6),
    )

    assert item.trace.ranker == "life_rec_weighted_v0"
    assert "amap.poi" in item.trace.data_sources
    assert "budget_fit_low" in item.trace.penalties
    assert "distance_cost_high" in item.trace.penalties
    assert any(entry.startswith("preference=") for entry in item.trace.evidence)
    assert 0 <= item.trace.confidence <= 1


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
    assert response.life_state is not None
    assert response.life_state.source_counts["meals"] == 1
    assert response.life_state.vector["meal_signal"] > 0
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
    assert response.life_state is not None
    assert response.life_state.source_counts["wellness"] == 1
    assert response.life_state.vector["wellness_signal"] > 0
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
    assert response.life_state is not None
    assert response.life_state.source_counts["preferences"] == 6
    assert response.life_state.vector["preference_signal"] > 0
    assert "地点：南京江宁" in response.intent_summary
    assert "预算：42 元" in response.intent_summary


def test_recommend_applies_plan_aware_ranking(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "liferec-test.sqlite3")
    monkeypatch.setattr(recommender, "settings", SimpleNamespace(strict_real_data=False, amap_api_key=None))

    storage.save_plan_item(
        user_id="u-plan-ranker",
        request_id="req-active",
        item_id="r001",
        item_name="绿野轻食",
        item_type="restaurant",
        title="今晚已计划绿野轻食",
        tags=["清淡", "沙拉"],
        source="local-json",
    )

    response = recommender.recommend(
        message="今晚想吃清淡一点",
        scenario="restaurant",
        user_id="u-plan-ranker",
    )

    assert response.recommendations
    duplicate = next((item for item in response.recommendations if item.id == "r001"), None)
    assert duplicate is not None
    assert duplicate.plan_signal.duplicate_active is True
    assert duplicate.plan_signal.adjustment < 0
    assert "active_plan_duplicate" in duplicate.plan_signal.blockers
