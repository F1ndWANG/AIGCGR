from __future__ import annotations

from typing import Any

from .models import ExecutionScore, RecommendationItem


WEATHER_RISK_WORDS = ("雨", "雪", "雾", "霾", "storm", "rain", "snow", "fog", "haze")


def score_execution(
    item: RecommendationItem,
    *,
    scenario: str,
    radius_km: float | None = None,
    budget: float | None = None,
    weather_context: dict[str, Any] | None = None,
) -> ExecutionScore:
    meta = item.meta or {}
    weather_context = weather_context or {}

    distance_cost, distance_evidence, distance_blockers = _distance_cost(item, meta, scenario, radius_km)
    budget_cost, budget_evidence, budget_blockers = _budget_cost(meta, budget)
    time_cost, time_evidence, time_blockers = _time_cost(item, meta, scenario)
    weather_cost, weather_evidence, weather_blockers = _weather_cost(meta, scenario, weather_context)
    complexity_cost, complexity_evidence, complexity_blockers = _complexity_cost(item, scenario)
    data_risk, data_evidence, data_blockers = _data_risk(meta)

    execution_cost = _bounded(
        0.23 * distance_cost
        + 0.18 * budget_cost
        + 0.18 * time_cost
        + 0.14 * weather_cost
        + 0.14 * complexity_cost
        + 0.13 * data_risk
    )
    executable_score = _bounded(1 - execution_cost)
    blockers = [
        *distance_blockers,
        *budget_blockers,
        *time_blockers,
        *weather_blockers,
        *complexity_blockers,
        *data_blockers,
    ]
    evidence = [
        *distance_evidence,
        *budget_evidence,
        *time_evidence,
        *weather_evidence,
        *complexity_evidence,
        *data_evidence,
    ]
    confidence = _bounded(0.45 + (1 - data_risk) * 0.35 + min(len(evidence), 6) * 0.025 - len(blockers) * 0.03)

    return ExecutionScore(
        executable_score=executable_score,
        execution_cost=execution_cost,
        distance_cost=distance_cost,
        budget_cost=budget_cost,
        time_cost=time_cost,
        weather_cost=weather_cost,
        complexity_cost=complexity_cost,
        data_risk=data_risk,
        blockers=blockers[:8],
        evidence=evidence[:8],
        confidence=confidence,
    )


def apply_execution_scores(
    items: list[RecommendationItem],
    *,
    scenario: str,
    radius_km: float | None = None,
    budget: float | None = None,
    weather_context: dict[str, Any] | None = None,
) -> list[RecommendationItem]:
    scored: list[RecommendationItem] = []
    for item in items:
        execution = score_execution(
            item,
            scenario=scenario,
            radius_km=radius_km,
            budget=budget,
            weather_context=weather_context,
        )
        item.execution = execution
        item.score_breakdown.execution = execution.executable_score
        item.score = round(item.score * 0.9 + execution.executable_score * 10, 1)
        item.trace.evidence.append(f"execution={execution.executable_score}")
        if execution.blockers:
            item.trace.penalties.extend([f"execution:{blocker}" for blocker in execution.blockers[:3]])
        scored.append(item)
    return sorted(scored, key=lambda candidate: (candidate.score, candidate.execution.executable_score), reverse=True)


def _distance_cost(
    item: RecommendationItem,
    meta: dict[str, Any],
    scenario: str,
    radius_km: float | None,
) -> tuple[float, list[str], list[str]]:
    if item.type == "product":
        return 0.05, ["distance=not_required"], []
    distance_km = _number(meta.get("distance_km"))
    route_distance = _number(meta.get("route_distance_meters"))
    if distance_km is None and route_distance is not None:
        distance_km = route_distance / 1000
    if distance_km is None:
        return 0.45, ["distance=unknown"], ["distance_unknown"]

    divisor = max((radius_km or 0) * 1.25, 1.0)
    if scenario == "travel":
        divisor = max(divisor, 20)
    cost = _bounded(distance_km / divisor)
    blockers = ["distance_high"] if cost >= 0.75 else []
    return cost, [f"distance_km={round(distance_km, 2)}"], blockers


def _budget_cost(meta: dict[str, Any], budget: float | None) -> tuple[float, list[str], list[str]]:
    price = _number(meta.get("avg_price")) or _number(meta.get("price")) or _number(meta.get("budget"))
    if budget is None or budget <= 0:
        return 0.2 if price is not None else 0.35, ["budget=request_missing"], []
    if price is None:
        return 0.35, [f"budget_limit={budget:g}", "price=unknown"], ["price_unknown"]
    ratio = price / budget
    if ratio <= 1:
        return _bounded(abs(0.75 - ratio) * 0.25), [f"price_ratio={round(ratio, 2)}"], []
    cost = _bounded(0.45 + (ratio - 1) * 0.65)
    return cost, [f"price_ratio={round(ratio, 2)}"], ["budget_exceeded"]


def _time_cost(item: RecommendationItem, meta: dict[str, Any], scenario: str) -> tuple[float, list[str], list[str]]:
    if item.type == "product":
        return 0.12, ["time=low_setup"], []
    minutes = _number(meta.get("route_duration_minutes"))
    if minutes is None:
        if meta.get("data_type") == "real-poi" and scenario in {"restaurant", "travel"}:
            return 0.3, ["route_time=unknown"], ["route_time_unknown"]
        return 0.25, ["route_time=not_available"], []
    cost = _bounded(minutes / 45)
    blockers = ["time_high"] if cost >= 0.75 else []
    return cost, [f"route_minutes={round(minutes, 1)}"], blockers


def _weather_cost(
    meta: dict[str, Any],
    scenario: str,
    weather_context: dict[str, Any],
) -> tuple[float, list[str], list[str]]:
    weather = str(weather_context.get("weather") or "")
    temperature = _number(weather_context.get("temperature"))
    if not weather and temperature is None:
        return 0.25, ["weather=unknown"], []

    risk = 0.05
    blockers: list[str] = []
    if any(word in weather.lower() for word in WEATHER_RISK_WORDS) or any(word in weather for word in WEATHER_RISK_WORDS):
        walk_km = (_number(meta.get("route_distance_meters")) or 0) / 1000
        risk = 0.45 if scenario in {"restaurant", "travel"} else 0.25
        if walk_km >= 1.2:
            risk = 0.75
            blockers.append("weather_walk_risk")
        else:
            blockers.append("weather_friction")
    if temperature is not None and (temperature >= 32 or temperature <= 3):
        risk = max(risk, 0.55)
        blockers.append("temperature_friction")
    return _bounded(risk), [f"weather={weather or 'temperature-only'}"], blockers


def _complexity_cost(item: RecommendationItem, scenario: str) -> tuple[float, list[str], list[str]]:
    suggestion_count = len(item.suggested_items or [])
    if scenario == "shopping":
        cost = _bounded(0.2 + max(suggestion_count - 3, 0) * 0.08)
    elif scenario == "travel":
        cost = _bounded(0.3 + max(suggestion_count - 2, 0) * 0.1)
    else:
        cost = _bounded(0.15 + max(suggestion_count - 2, 0) * 0.08)
    blockers = ["decision_complexity_high"] if cost >= 0.65 else []
    return cost, [f"suggestion_count={suggestion_count}"], blockers


def _data_risk(meta: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    source = str(meta.get("source") or meta.get("provider") or "")
    data_type = str(meta.get("data_type") or "")
    if data_type == "real-poi" or source == "amap":
        return 0.05, [f"source={source or data_type}"], []
    if data_type == "aigc-product-need" or source == "aigc":
        return 0.32, ["source=aigc_product_need"], []
    if "sample" in source or "sample" in data_type:
        return 0.75, [f"source={source or data_type}"], ["sample_data"]
    return 0.45, [f"source={source or 'unknown'}"], ["source_uncertain"]


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bounded(value: float) -> float:
    return round(max(0, min(1, value)), 3)
