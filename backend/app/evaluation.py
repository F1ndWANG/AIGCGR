from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .models import RecommendationRequest, RecommendationResponse


Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class EvaluationIssue:
    rule: str
    severity: Severity
    message: str
    item_id: str | None = None
    item_name: str | None = None


def evaluate_recommendation(request: RecommendationRequest, response: RecommendationResponse) -> dict[str, Any]:
    issues: list[EvaluationIssue] = []
    issues.extend(_check_duplicates(response))
    issues.extend(_check_excluded_items(request, response))
    issues.extend(_check_budget(request, response))
    issues.extend(_check_distance(request, response))
    issues.extend(_check_real_data_policy(response))
    issues.extend(_check_health_constraints(request, response))
    issues.extend(_check_execution_cost(response))
    issues.extend(_check_realness_guard(response))

    errors = [issue for issue in issues if issue.severity == "error"]
    warnings = [issue for issue in issues if issue.severity == "warning"]
    return {
        "passed": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "recommendation_count": len(response.recommendations),
        "average_executable_score": _average_executable_score(response),
        "average_realness_score": _average_realness_score(response),
        "issues": [issue.__dict__ for issue in issues],
    }


def _check_duplicates(response: RecommendationResponse) -> list[EvaluationIssue]:
    issues: list[EvaluationIssue] = []
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    for item in response.recommendations:
        if item.id in seen_ids:
            issues.append(EvaluationIssue("duplicate_item_id", "error", "推荐结果中存在重复 item id。", item.id, item.name))
        if item.name in seen_names:
            issues.append(EvaluationIssue("duplicate_item_name", "warning", "推荐结果中存在重复 item name。", item.id, item.name))
        seen_ids.add(item.id)
        seen_names.add(item.name)
    return issues


def _check_excluded_items(request: RecommendationRequest, response: RecommendationResponse) -> list[EvaluationIssue]:
    excluded_ids = set(request.exclude_item_ids)
    excluded_names = set(request.exclude_item_names)
    issues: list[EvaluationIssue] = []
    for item in response.recommendations:
        if item.id in excluded_ids or item.name in excluded_names:
            issues.append(EvaluationIssue("excluded_item_returned", "error", "换一批或排除列表中的 item 被重新返回。", item.id, item.name))
    return issues


def _check_budget(request: RecommendationRequest, response: RecommendationResponse) -> list[EvaluationIssue]:
    if not request.budget:
        return []
    issues: list[EvaluationIssue] = []
    for item in response.recommendations:
        price = _first_number(item.meta, ["price", "avg_price", "budget"])
        if price is None:
            continue
        if price > request.budget * 1.2:
            issues.append(
                EvaluationIssue(
                    "budget_exceeded",
                    "warning",
                    f"候选价格或预算 {price:g} 超过用户预算 {request.budget:g} 的 120%。",
                    item.id,
                    item.name,
                )
            )
    return issues


def _check_distance(request: RecommendationRequest, response: RecommendationResponse) -> list[EvaluationIssue]:
    issues: list[EvaluationIssue] = []
    for item in response.recommendations:
        distance = _first_number(item.meta, ["distance_km"])
        if distance is None:
            continue
        if distance > request.radius_km:
            issues.append(
                EvaluationIssue(
                    "distance_exceeded",
                    "error",
                    f"候选距离 {distance:g}km 超过请求半径 {request.radius_km:g}km。",
                    item.id,
                    item.name,
                )
            )
    return issues


def _check_real_data_policy(response: RecommendationResponse) -> list[EvaluationIssue]:
    if response.context.get("data_source_policy") != "real-provider-only":
        return []

    disallowed_sources = {"local-json", "sample-data", "sample-distance", "dynamic-location", "fallback"}
    issues: list[EvaluationIssue] = []
    for item in response.recommendations:
        source = str(item.meta.get("source") or "")
        data_type = str(item.meta.get("data_type") or "")
        if source in disallowed_sources or data_type == "sample-data":
            issues.append(
                EvaluationIssue(
                    "strict_real_data_violation",
                    "error",
                    f"严格真实数据模式下返回了非真实 Provider 数据：source={source}, data_type={data_type}。",
                    item.id,
                    item.name,
                )
            )
    return issues


def _check_health_constraints(request: RecommendationRequest, response: RecommendationResponse) -> list[EvaluationIssue]:
    if "高油" not in request.recent_meal_tags:
        return []
    issues: list[EvaluationIssue] = []
    avoid_tags = {"油炸", "重油"}
    for item in response.recommendations:
        matched = avoid_tags.intersection(item.tags)
        if matched:
            issues.append(
                EvaluationIssue(
                    "health_conflict",
                    "warning",
                    f"用户近期高油，候选仍包含不利标签：{', '.join(sorted(matched))}。",
                    item.id,
                    item.name,
                )
            )
    return issues


def _check_execution_cost(response: RecommendationResponse) -> list[EvaluationIssue]:
    issues: list[EvaluationIssue] = []
    for item in response.recommendations:
        if item.execution.executable_score < 0.35:
            blockers = ", ".join(item.execution.blockers[:4]) or "high_execution_cost"
            issues.append(
                EvaluationIssue(
                    "low_executable_score",
                    "warning",
                    f"候选可执行性较低：score={item.execution.executable_score:g}, blockers={blockers}。",
                    item.id,
                    item.name,
                )
            )
    return issues


def _check_realness_guard(response: RecommendationResponse) -> list[EvaluationIssue]:
    issues: list[EvaluationIssue] = []
    for item in response.recommendations:
        if item.realness.forbidden_claims:
            issues.append(
                EvaluationIssue(
                    "aigc_forbidden_claim",
                    "error" if response.context.get("data_source_policy") == "real-provider-only" else "warning",
                    f"AIGC/非Provider内容包含禁止声明：{', '.join(item.realness.forbidden_claims)}。",
                    item.id,
                    item.name,
                )
            )
        elif item.realness.hallucination_risk >= 0.7:
            issues.append(
                EvaluationIssue(
                    "high_hallucination_risk",
                    "warning",
                    f"候选幻觉风险较高：risk={item.realness.hallucination_risk:g}, label={item.realness.label}。",
                    item.id,
                    item.name,
                )
            )
    return issues


def _average_executable_score(response: RecommendationResponse) -> float | None:
    if not response.recommendations:
        return None
    return round(
        sum(item.execution.executable_score for item in response.recommendations) / len(response.recommendations),
        3,
    )


def _average_realness_score(response: RecommendationResponse) -> float | None:
    if not response.recommendations:
        return None
    return round(
        sum(item.realness.realness_score for item in response.recommendations) / len(response.recommendations),
        3,
    )


def _first_number(meta: dict[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        value = meta.get(key)
        if value in ("", None):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None
