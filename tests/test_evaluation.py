from __future__ import annotations

from app.evaluation import evaluate_recommendation
from app.models import RecommendationItem, RecommendationRequest, RecommendationResponse, ScoreBreakdown


def test_evaluation_passes_real_provider_result() -> None:
    request = RecommendationRequest(
        message="推荐附近清淡餐厅",
        scenario="restaurant",
        radius_km=3,
        budget=50,
        recent_meal_tags=["高油"],
    )
    response = _response([
        _item(
            item_id="amap-1",
            name="真实餐厅",
            tags=["清淡"],
            meta={"source": "amap", "data_type": "real-poi", "distance_km": 1.2, "avg_price": 42},
        )
    ])

    report = evaluate_recommendation(request, response)
    assert report["passed"] is True
    assert report["error_count"] == 0


def test_evaluation_catches_excluded_and_distance_violations() -> None:
    request = RecommendationRequest(
        message="换一批",
        scenario="restaurant",
        radius_km=2,
        exclude_item_ids=["old-1"],
    )
    response = _response([
        _item(
            item_id="old-1",
            name="旧餐厅",
            tags=[],
            meta={"source": "amap", "data_type": "real-poi", "distance_km": 3.5},
        )
    ])

    report = evaluate_recommendation(request, response)
    assert report["passed"] is False
    assert {issue["rule"] for issue in report["issues"]} == {"excluded_item_returned", "distance_exceeded"}


def test_evaluation_catches_strict_real_data_violation() -> None:
    request = RecommendationRequest(message="推荐餐厅", scenario="restaurant")
    response = _response([
        _item(
            item_id="sample-1",
            name="样例餐厅",
            tags=[],
            meta={"source": "sample-data", "data_type": "sample-data"},
        )
    ])

    report = evaluate_recommendation(request, response)
    assert report["passed"] is False
    assert report["issues"][0]["rule"] == "strict_real_data_violation"


def _response(items: list[RecommendationItem]) -> RecommendationResponse:
    return RecommendationResponse(
        request_id="req-test",
        scenario="restaurant",
        intent_summary="测试",
        health_summary="测试",
        strategy="测试",
        context={"data_source_policy": "real-provider-only"},
        recommendations=items,
        plan=[],
        follow_up_questions=[],
        safety_note="测试",
    )


def _item(item_id: str, name: str, tags: list[str], meta: dict[str, str | float | int]) -> RecommendationItem:
    return RecommendationItem(
        id=item_id,
        name=name,
        type="restaurant",
        score=80,
        tags=tags,
        reasons=["测试"],
        meta=meta,
        score_breakdown=ScoreBreakdown(preference=0.5, health=0.5, budget=0.5, distance=0.5, context=0.5),
    )
