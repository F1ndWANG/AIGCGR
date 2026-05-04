from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import PlanSignal, RecommendationItem


DONE_TAG_WEIGHT = 6.0
CANCELED_TAG_WEIGHT = -7.0
ACTIVE_TAG_WEIGHT = -8.0
ACTIVE_DUPLICATE_WEIGHT = -24.0
CANCELED_DUPLICATE_WEIGHT = -16.0


def apply_plan_aware_ranking(items: list[RecommendationItem], plans: list[dict[str, Any]]) -> list[RecommendationItem]:
    if not items:
        return items
    if not plans:
        return items

    active = [_normalize_plan(plan) for plan in plans if plan.get("status") == "active"]
    done = [_normalize_plan(plan) for plan in plans if plan.get("status") == "done"]
    canceled = [_normalize_plan(plan) for plan in plans if plan.get("status") == "canceled"]

    ranked: list[RecommendationItem] = []
    for item in items:
        signal = score_plan_signal(item, active=active, done=done, canceled=canceled)
        item.plan_signal = signal
        item.score = round(max(0, item.score + signal.adjustment), 1)
        if signal.adjustment:
            item.meta["plan_adjustment"] = round(signal.adjustment, 2)
        if signal.evidence:
            item.trace.evidence.append(f"plan_adjustment={round(signal.adjustment, 2)}")
        if signal.blockers:
            item.trace.penalties.extend([f"plan:{blocker}" for blocker in signal.blockers[:3]])
        ranked.append(item)
    return sorted(ranked, key=lambda candidate: (candidate.score, candidate.execution.executable_score), reverse=True)


def score_plan_signal(
    item: RecommendationItem,
    *,
    active: list[dict[str, Any]],
    done: list[dict[str, Any]],
    canceled: list[dict[str, Any]],
) -> PlanSignal:
    item_tags = set(item.tags or [])
    evidence: list[str] = []
    blockers: list[str] = []
    adjustment = 0.0

    duplicate_active = any(_same_item(item, plan) for plan in active)
    if duplicate_active:
        adjustment += ACTIVE_DUPLICATE_WEIGHT
        evidence.append("active_duplicate=-24")
        blockers.append("active_plan_duplicate")

    active_overlap = _max_tag_overlap(item_tags, active)
    if active_overlap:
        penalty = ACTIVE_TAG_WEIGHT * active_overlap
        adjustment += penalty
        evidence.append(f"active_tag_overlap={round(active_overlap, 2)}")
        if active_overlap >= 0.5:
            blockers.append("active_plan_overlap")

    completed_tag_boost = _max_tag_overlap(item_tags, done)
    if completed_tag_boost:
        boost = DONE_TAG_WEIGHT * completed_tag_boost
        adjustment += boost
        evidence.append(f"done_tag_boost={round(completed_tag_boost, 2)}")

    canceled_tag_penalty = _max_tag_overlap(item_tags, canceled)
    if canceled_tag_penalty:
        penalty = CANCELED_TAG_WEIGHT * canceled_tag_penalty
        adjustment += penalty
        evidence.append(f"canceled_tag_penalty={round(canceled_tag_penalty, 2)}")
        if canceled_tag_penalty >= 0.5:
            blockers.append("canceled_plan_overlap")

    if any(_same_item(item, plan) for plan in canceled):
        adjustment += CANCELED_DUPLICATE_WEIGHT
        evidence.append("canceled_duplicate=-16")
        blockers.append("canceled_plan_duplicate")

    schedule_conflict = any(_scheduled_active_conflict(plan) for plan in active if _same_item(item, plan) or _tag_overlap(item_tags, plan["tags"]) >= 0.5)
    if schedule_conflict:
        adjustment -= 6
        evidence.append("schedule_conflict=-6")
        blockers.append("scheduled_active_plan_conflict")

    return PlanSignal(
        adjustment=round(adjustment, 2),
        duplicate_active=duplicate_active,
        schedule_conflict=schedule_conflict,
        completed_tag_boost=round(completed_tag_boost, 3),
        canceled_tag_penalty=round(canceled_tag_penalty, 3),
        active_overlap=round(active_overlap, 3),
        evidence=evidence,
        blockers=blockers,
    )


def _normalize_plan(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_id": str(plan.get("item_id") or ""),
        "item_name": str(plan.get("item_name") or ""),
        "item_type": str(plan.get("item_type") or ""),
        "tags": {str(tag).strip() for tag in plan.get("tags", []) if str(tag).strip()},
        "scheduled_for": plan.get("scheduled_for"),
        "status": plan.get("status"),
    }


def _same_item(item: RecommendationItem, plan: dict[str, Any]) -> bool:
    return bool(item.id and item.id == plan["item_id"]) or bool(item.name and item.name == plan["item_name"])


def _max_tag_overlap(tags: set[str], plans: list[dict[str, Any]]) -> float:
    if not tags or not plans:
        return 0
    return max((_tag_overlap(tags, plan["tags"]) for plan in plans), default=0)


def _tag_overlap(tags: set[str], plan_tags: set[str]) -> float:
    if not tags or not plan_tags:
        return 0
    return len(tags.intersection(plan_tags)) / max(len(tags), len(plan_tags), 1)


def _scheduled_active_conflict(plan: dict[str, Any]) -> bool:
    value = plan.get("scheduled_for")
    if not value:
        return False
    try:
        scheduled = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return True
    if scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=timezone.utc)
    return scheduled >= datetime.now(timezone.utc)
