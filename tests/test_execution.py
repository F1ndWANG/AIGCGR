from __future__ import annotations

from app.execution import apply_execution_scores, score_execution
from app.models import RecommendationItem, ScoreBreakdown


def _candidate(
    *,
    item_id: str,
    score: float,
    meta: dict[str, str | float | int],
    suggested_items: list[str] | None = None,
) -> RecommendationItem:
    return RecommendationItem(
        id=item_id,
        name=item_id,
        type="restaurant",
        score=score,
        tags=["light"],
        reasons=["test"],
        suggested_items=suggested_items or [],
        meta=meta,
        score_breakdown=ScoreBreakdown(preference=0.7, health=0.8, budget=0.7, distance=0.7, context=0.6),
    )


def test_execution_scorer_penalizes_high_distance_budget_and_weather() -> None:
    item = _candidate(
        item_id="far-expensive",
        score=80,
        suggested_items=["a", "b", "c", "d"],
        meta={
            "distance_km": 5.0,
            "avg_price": 120,
            "route_distance_meters": 4500,
            "route_duration_minutes": 52,
            "source": "amap",
            "data_type": "real-poi",
        },
    )

    execution = score_execution(
        item,
        scenario="restaurant",
        radius_km=2,
        budget=60,
        weather_context={"weather": "rain"},
    )

    assert execution.executable_score < 0.5
    assert "distance_high" in execution.blockers
    assert "budget_exceeded" in execution.blockers
    assert "time_high" in execution.blockers
    assert any(entry.startswith("distance_km=") for entry in execution.evidence)


def test_execution_reranking_can_promote_low_burden_candidate() -> None:
    hard = _candidate(
        item_id="hard",
        score=82,
        suggested_items=["a", "b", "c", "d"],
        meta={
            "distance_km": 5.0,
            "avg_price": 120,
            "route_duration_minutes": 55,
            "source": "amap",
            "data_type": "real-poi",
        },
    )
    easy = _candidate(
        item_id="easy",
        score=78,
        suggested_items=["a"],
        meta={
            "distance_km": 0.4,
            "avg_price": 45,
            "route_duration_minutes": 8,
            "source": "amap",
            "data_type": "real-poi",
        },
    )

    ranked = apply_execution_scores(
        [hard, easy],
        scenario="restaurant",
        radius_km=2,
        budget=60,
        weather_context={"weather": "晴"},
    )

    assert ranked[0].id == "easy"
    assert ranked[0].execution.executable_score > ranked[1].execution.executable_score
    assert ranked[0].score_breakdown.execution == ranked[0].execution.executable_score
    assert any(entry.startswith("execution=") for entry in ranked[0].trace.evidence)
