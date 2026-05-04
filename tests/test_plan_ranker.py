from __future__ import annotations

from app.models import RecommendationItem, ScoreBreakdown
from app.plan_ranker import apply_plan_aware_ranking, score_plan_signal


def _item(item_id: str, tags: list[str], score: float = 80) -> RecommendationItem:
    return RecommendationItem(
        id=item_id,
        name=item_id,
        type="restaurant",
        score=score,
        tags=tags,
        reasons=["test"],
        meta={"source": "amap", "data_type": "real-poi"},
        score_breakdown=ScoreBreakdown(preference=0.6, health=0.7, budget=0.8, distance=0.8, context=0.6),
    )


def _plan(item_id: str, status: str, tags: list[str], scheduled_for: str | None = None) -> dict[str, object]:
    return {
        "item_id": item_id,
        "item_name": item_id,
        "item_type": "restaurant",
        "status": status,
        "tags": tags,
        "scheduled_for": scheduled_for,
    }


def test_plan_signal_penalizes_active_duplicate_and_schedule_conflict() -> None:
    item = _item("same-plan", ["light", "nearby"])
    signal = score_plan_signal(
        item,
        active=[_plan("same-plan", "active", ["light"], "2030-01-02T03:04:00+00:00")],
        done=[],
        canceled=[],
    )

    assert signal.duplicate_active is True
    assert signal.schedule_conflict is True
    assert signal.adjustment < -20
    assert "active_plan_duplicate" in signal.blockers
    assert "scheduled_active_plan_conflict" in signal.blockers


def test_plan_aware_ranking_boosts_done_tags_and_penalizes_canceled_tags() -> None:
    preferred = _item("preferred", ["protein", "light"], score=70)
    rejected = _item("rejected", ["fried", "heavy"], score=72)

    ranked = apply_plan_aware_ranking(
        [rejected, preferred],
        plans=[
            _plan("done-plan", "done", ["protein", "light"]),
            _plan("canceled-plan", "canceled", ["fried", "heavy"]),
        ],
    )

    assert ranked[0].id == "preferred"
    assert ranked[0].plan_signal.completed_tag_boost > 0
    assert ranked[1].plan_signal.canceled_tag_penalty > 0
    assert any(entry.startswith("plan_adjustment=") for entry in ranked[0].trace.evidence)
