from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import LifeStateSnapshot


POSITIVE_ACTIONS = {"like", "save", "plan", "done"}
NEGATIVE_ACTIONS = {"dislike", "skip", "canceled"}


def encode_life_state(
    *,
    user_id: str,
    meals: list[Any] | None = None,
    wellness: list[Any] | None = None,
    preferences: Any | None = None,
    feedback: Any | None = None,
    plans: list[Any] | None = None,
    recommendations: list[Any] | None = None,
    recent_meal_tags: list[str] | None = None,
    recent_wellness_tags: list[str] | None = None,
) -> LifeStateSnapshot:
    meal_rows = [_as_dict(item) for item in meals or []]
    wellness_rows = [_as_dict(item) for item in wellness or []]
    preference_data = _as_dict(preferences or {})
    feedback_data = _as_dict(feedback or {})
    plan_rows = [_as_dict(item) for item in plans or []]
    recommendation_rows = [_as_dict(item) for item in recommendations or []]

    meal_tags = _dedupe(recent_meal_tags or _tags_from_rows(meal_rows))
    wellness_tags = _dedupe(recent_wellness_tags or _tags_from_rows(wellness_rows))
    short_term_tags = _dedupe([*meal_tags, *wellness_tags])[:12]
    long_term_tags = _preference_tags(preference_data)
    constraints = _dedupe(
        [
            *_list_value(preference_data.get("avoid")),
            *_list_value(preference_data.get("allergies")),
            *[tag for tag in short_term_tags if _looks_like_constraint(tag)],
        ]
    )[:10]

    feedback_events = [_as_dict(item) for item in feedback_data.get("events", []) or []]
    positive_feedback_count = sum(1 for item in feedback_events if item.get("action") in POSITIVE_ACTIONS)
    negative_feedback_count = sum(1 for item in feedback_events if item.get("action") in NEGATIVE_ACTIONS)
    active_plan_count = len(plan_rows)
    scheduled_plan_count = sum(1 for item in plan_rows if item.get("scheduled_for"))

    source_counts = {
        "meals": len(meal_rows),
        "wellness": len(wellness_rows),
        "preferences": len(long_term_tags),
        "feedback_events": len(feedback_events),
        "plans": active_plan_count,
        "recommendations": len(recommendation_rows),
    }
    vector = {
        "meal_signal": _bounded(len(meal_tags) / 8),
        "wellness_signal": _bounded(len(wellness_tags) / 8),
        "preference_signal": _bounded(len(long_term_tags) / 10),
        "feedback_signal": _bounded(len(feedback_events) / 10),
        "plan_signal": _bounded(active_plan_count / 8),
        "history_signal": _bounded(len(recommendation_rows) / 10),
        "schedule_signal": _bounded(scheduled_plan_count / max(active_plan_count, 1)),
    }
    completeness = _bounded(sum(1 for value in source_counts.values() if value > 0) / len(source_counts))
    confidence = _bounded(0.35 + completeness * 0.55 + vector["schedule_signal"] * 0.1)

    return LifeStateSnapshot(
        user_id=user_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        short_term_tags=short_term_tags,
        long_term_tags=long_term_tags[:12],
        constraints=constraints,
        active_plan_count=active_plan_count,
        scheduled_plan_count=scheduled_plan_count,
        recommendation_count=len(recommendation_rows),
        positive_feedback_count=positive_feedback_count,
        negative_feedback_count=negative_feedback_count,
        context_completeness=completeness,
        confidence=confidence,
        source_counts=source_counts,
        vector=vector,
        warnings=_warnings(source_counts),
    )


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return {}


def _tags_from_rows(rows: list[dict[str, Any]]) -> list[str]:
    tags: list[str] = []
    for row in rows:
        tags.extend(_list_value(row.get("tags")))
    return tags


def _preference_tags(preferences: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    for key in ("taste", "avoid", "allergies", "health_goals", "travel_style"):
        tags.extend(_list_value(preferences.get(key)))
    if preferences.get("default_location"):
        tags.append(f"location:{preferences['default_location']}")
    if preferences.get("default_budget"):
        tags.append(f"budget:{preferences['default_budget']}")
    return _dedupe(tags)


def _list_value(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _looks_like_constraint(tag: str) -> bool:
    lower = tag.lower()
    tokens = ("high", "low", "lack", "stress", "sleep", "不足", "偏高", "高", "少", "压力", "熬夜")
    return any(token in lower for token in tokens)


def _warnings(source_counts: dict[str, int]) -> list[str]:
    warnings: list[str] = []
    if source_counts["meals"] == 0:
        warnings.append("missing_meal_history")
    if source_counts["wellness"] == 0:
        warnings.append("missing_wellness_history")
    if source_counts["preferences"] == 0:
        warnings.append("missing_long_term_preferences")
    if source_counts["feedback_events"] == 0:
        warnings.append("missing_feedback")
    if source_counts["recommendations"] == 0:
        warnings.append("missing_recommendation_history")
    return warnings


def _bounded(value: float) -> float:
    return round(max(0, min(1, value)), 3)
