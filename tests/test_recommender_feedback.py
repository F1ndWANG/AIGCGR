from __future__ import annotations

from app.models import RecommendationItem, ScoreBreakdown
from app.recommender import _apply_feedback_profile


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
