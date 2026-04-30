from __future__ import annotations

import math
import re
from uuid import uuid4
from dataclasses import dataclass
from typing import Any

from .aigc import build_life_brief
from .config import settings
from .data_loader import load_dataset
from .geo import haversine_km
from .models import NearbyPlace, RecommendationItem, RecommendationResponse, RouteResponse, ScoreBreakdown, WeatherResponse
from .product_providers import get_product_provider
from .providers import get_place_provider
from .storage import feedback_summary, recent_meal_tags as load_recent_meal_tags, save_recommendation_event


SCENARIO_KEYWORDS = {
    "diet": ["吃", "饭", "饮食", "健康", "油腻", "清淡", "减脂", "肠胃", "不想吃饭"],
    "restaurant": ["餐厅", "附近", "店", "菜", "外卖", "堂食", "预算"],
    "shopping": ["买", "购物", "清单", "商品", "装备", "食材", "导购"],
    "travel": ["旅游", "旅行", "周末", "出发", "景点", "行程", "玩", "路线"],
}

HEALTH_RULES = {
    "高油": {"prefer": ["低油", "清淡", "蒸煮", "轻食"], "avoid": ["油炸", "重油"]},
    "高盐": {"prefer": ["少盐", "清淡", "汤粥"], "avoid": ["腌制", "重口"]},
    "蔬菜少": {"prefer": ["蔬菜", "沙拉", "菌菇"], "avoid": []},
    "蛋白不足": {"prefer": ["高蛋白", "鸡肉", "鱼肉", "豆制品"], "avoid": []},
    "碳水偏高": {"prefer": ["高蛋白", "低碳水", "粗粮"], "avoid": ["甜品"]},
}


@dataclass
class ParsedIntent:
    scenario: str
    keywords: list[str]
    budget: float | None
    location: str | None
    latitude: float | None
    longitude: float | None
    radius_km: float
    constraints: list[str]


def recommend(
    message: str,
    scenario: str = "auto",
    user_id: str = "u001",
    location: str | None = None,
    budget: float | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    radius_km: float = 3.0,
    taste: list[str] | None = None,
    avoid: list[str] | None = None,
    allergies: list[str] | None = None,
    health_goals: list[str] | None = None,
    recent_meal_tags: list[str] | None = None,
    travel_style: list[str] | None = None,
    exclude_item_ids: list[str] | None = None,
    exclude_item_names: list[str] | None = None,
    request_payload: dict[str, Any] | None = None,
) -> RecommendationResponse:
    dataset = load_dataset()
    supplied_recent_meal_tags = recent_meal_tags or []
    stored_recent_meal_tags = [] if supplied_recent_meal_tags else load_recent_meal_tags(user_id)
    effective_recent_meal_tags = supplied_recent_meal_tags or stored_recent_meal_tags
    user = _build_user_profile(
        _find_user(dataset["users"], user_id),
        budget=budget,
        taste=taste or [],
        avoid=avoid or [],
        allergies=allergies or [],
        health_goals=health_goals or [],
        recent_meal_tags=effective_recent_meal_tags,
        travel_style=travel_style or [],
    )
    intent = parse_intent(message, scenario, location, budget, user, latitude, longitude, radius_km)
    health_tags = analyze_health_state(user)
    weather_context = _load_weather_context(intent)
    feedback_profile = feedback_summary(user_id)

    if intent.scenario == "travel":
        items = _recommend_travel(dataset, user, intent)
        plan = _build_travel_plan(items, intent, weather_context)
    elif intent.scenario == "shopping":
        items = _recommend_products(dataset, user, intent, health_tags)
        plan = _build_shopping_plan(items, weather_context)
    else:
        items = _recommend_restaurants(dataset, user, intent, health_tags)
        plan = _build_food_plan(items, health_tags, weather_context)

    items = _apply_feedback_profile(items, feedback_profile)
    items = _exclude_items(items, exclude_item_ids or [], exclude_item_names or [])
    health_summary = _health_summary(health_tags)
    strategy = _strategy_summary(intent.scenario, health_tags)
    aigc_summary, _ = build_life_brief(message, intent.scenario, health_tags)
    request_id = str(uuid4())
    context = _context_summary(intent, weather_context)
    context["recent_meal_tags_source"] = "request" if supplied_recent_meal_tags else "runtime-storage"
    context["recent_meal_tag_count"] = len(effective_recent_meal_tags)
    response = RecommendationResponse(
        request_id=request_id,
        scenario=intent.scenario,
        intent_summary=_intent_summary(intent),
        health_summary=health_summary,
        strategy=strategy,
        context=context,
        aigc_summary=aigc_summary,
        recommendations=items[:5],
        plan=plan,
        follow_up_questions=_follow_ups(intent.scenario),
        safety_note="本系统只提供一般生活方式建议，不替代医生、营养师或其他专业人士的判断。",
    )
    save_recommendation_event(
        request_id=request_id,
        user_id=user_id,
        scenario=response.scenario,
        message=message,
        request_payload=request_payload or _request_payload(
            message=message,
            scenario=scenario,
            user_id=user_id,
            location=location,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            budget=budget,
            taste=taste or [],
            avoid=avoid or [],
            allergies=allergies or [],
            health_goals=health_goals or [],
            recent_meal_tags=effective_recent_meal_tags,
            travel_style=travel_style or [],
            exclude_item_ids=exclude_item_ids or [],
            exclude_item_names=exclude_item_names or [],
        ),
        context=response.context,
        recommendations=[item.model_dump() for item in response.recommendations],
    )
    return response


def parse_intent(
    message: str,
    scenario: str,
    location: str | None,
    budget: float | None,
    user: dict[str, Any],
    latitude: float | None = None,
    longitude: float | None = None,
    radius_km: float = 3.0,
) -> ParsedIntent:
    found_budget = budget if budget is not None else _extract_budget(message)
    found_location = location or _extract_location(message) or user.get("default_location")
    keywords = _tokenize(message)

    selected = scenario
    if scenario == "auto":
        if any(word in message for word in ["旅游", "旅行", "周末", "出发", "景点", "行程", "路线"]):
            selected = "travel"
        elif any(word in message for word in ["购物", "清单", "商品", "装备", "食材", "导购", "买"]):
            selected = "shopping"
        elif any(word in message for word in ["餐厅", "附近", "外卖", "堂食", "菜品"]):
            selected = "restaurant"
        else:
            scores = {
                key: sum(1 for word in words if word in message)
                for key, words in SCENARIO_KEYWORDS.items()
            }
            selected = max(scores, key=scores.get)
            if scores[selected] == 0:
                selected = "restaurant"

    if selected == "diet":
        selected = "restaurant"

    constraints = []
    for word in ["清淡", "低油", "高蛋白", "少辣", "不辣", "预算", "不太累", "周末", "健康"]:
        if word in message:
            constraints.append(word)

    return ParsedIntent(
        scenario=selected,
        keywords=keywords,
        budget=found_budget,
        location=found_location,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        constraints=constraints,
    )


def analyze_health_state(user: dict[str, Any]) -> list[str]:
    if settings.strict_real_data and not user.get("recent_meals"):
        return []

    tags: list[str] = []
    for meal in user.get("recent_meals", []):
        tags.extend(meal.get("tags", []))

    counts = {tag: tags.count(tag) for tag in set(tags)}
    result = [tag for tag, count in counts.items() if count >= 1 and tag in HEALTH_RULES]

    if "蔬菜" not in tags and "蔬菜少" not in result:
        result.append("蔬菜少")

    return result[:4]


def _recommend_restaurants(dataset: dict[str, Any], user: dict[str, Any], intent: ParsedIntent, health_tags: list[str]) -> list[RecommendationItem]:
    provider = get_place_provider()
    if _should_use_real_places(intent):
        places = _safe_places(lambda: provider.nearby(
            latitude=intent.latitude,
            longitude=intent.longitude,
            keyword="餐厅",
            radius_km=intent.radius_km,
        ))
        if places:
            return _recommend_from_real_places(places, user, intent, health_tags, item_type="restaurant")
    elif settings.amap_api_key and intent.location:
        places = _safe_places(lambda: provider.text_search(keyword="餐厅", city=intent.location, limit=12))
        if places:
            return _recommend_from_real_places(places, user, intent, health_tags, item_type="restaurant")

    if settings.strict_real_data:
        return []

    restaurants = dataset["restaurants"]
    dishes_by_id = {dish["id"]: dish for dish in dataset["dishes"]}
    budget = intent.budget or user.get("default_budget", 50)

    items = []
    for restaurant in restaurants:
        dynamic_distance = _dynamic_distance(restaurant, intent)
        if dynamic_distance is not None and dynamic_distance > intent.radius_km:
            continue
        candidate_dishes = [dishes_by_id[dish_id] for dish_id in restaurant["dish_ids"] if dish_id in dishes_by_id]
        suggested = _select_dishes(candidate_dishes, user, health_tags)
        combined_tags = set(restaurant.get("tags", []))
        for dish in suggested:
            combined_tags.update(dish.get("tags", []))

        preference = _tag_overlap_score(combined_tags, user.get("taste", []))
        health = _health_score(combined_tags, health_tags)
        budget_score = _budget_score(restaurant.get("avg_price", 0), budget)
        distance_km = dynamic_distance if dynamic_distance is not None else restaurant.get("distance_km", 5)
        distance = _distance_score(distance_km)
        context = _tag_overlap_score(combined_tags, intent.constraints + intent.keywords)
        score = _weighted_score(preference, health, budget_score, distance, context)

        reasons = _build_reasons(restaurant["name"], combined_tags, health_tags, budget_score, distance)
        items.append(_item(
            id=restaurant["id"],
            name=restaurant["name"],
            item_type="restaurant",
            score=score,
            tags=sorted(combined_tags),
            reasons=reasons,
            suggested_items=[dish["name"] for dish in suggested],
            meta={
                "avg_price": restaurant["avg_price"],
                "distance_km": round(distance_km, 2),
                "location": restaurant["location"],
                "source": "dynamic-location" if dynamic_distance is not None else "sample-distance",
            },
            breakdown=(preference, health, budget_score, distance, context),
        ))

    return sorted(items, key=lambda item: item.score, reverse=True)


def _recommend_products(dataset: dict[str, Any], user: dict[str, Any], intent: ParsedIntent, health_tags: list[str]) -> list[RecommendationItem]:
    budget = intent.budget or 300
    preferred_tags = _preferred_health_tags(health_tags) + intent.constraints + intent.keywords
    keyword = " ".join(intent.keywords[:6]) or "生活购物"
    provider = get_product_provider()
    products = provider.search(keyword=keyword, budget=budget, tags=preferred_tags, limit=8, scenario="shopping")

    items = []
    for product in products:
        tags = set(product.tags)
        preference = _tag_overlap_score(tags, user.get("taste", []))
        health = _tag_overlap_score(tags, preferred_tags)
        budget_score = _budget_score(product.price, budget) if product.price is not None else 0.55
        distance = 1.0
        context = _tag_overlap_score(tags, intent.keywords + intent.constraints)
        score = _weighted_score(preference, health, budget_score, distance, context)
        reasons = [product.reason or "由商品 Provider 根据当前生活目标生成。"]
        if product.purchase_hint:
            reasons.append(product.purchase_hint)
        if product.source == "aigc":
            reasons.append("该项来自 AIGC 商品需求生成，不代表真实 SKU、库存、折扣或购买链接。")
        items.append(_item(
            id=product.id,
            name=product.name,
            item_type="product",
            score=score,
            tags=sorted(tags),
            reasons=reasons,
            meta={
                "price": product.price or "",
                "category": product.category or "",
                "provider": product.provider,
                "source": product.source,
                "data_type": "aigc-product-need" if product.source == "aigc" else "sample-data",
            },
            breakdown=(preference, health, budget_score, distance, context),
        ))

    return sorted(items, key=lambda item: item.score, reverse=True)


def _recommend_travel(dataset: dict[str, Any], user: dict[str, Any], intent: ParsedIntent) -> list[RecommendationItem]:
    provider = get_place_provider()
    if _should_use_real_places(intent):
        places = _safe_places(lambda: provider.nearby(
            latitude=intent.latitude,
            longitude=intent.longitude,
            keyword="景点",
            radius_km=max(intent.radius_km, 20),
        ))
        if places:
            return _recommend_from_real_places(places, user, intent, [], item_type="destination")
    if settings.amap_api_key and intent.location:
        places = _safe_places(lambda: provider.text_search(keyword="景点", city=intent.location, limit=12))
        if places:
            return _recommend_from_real_places(places, user, intent, [], item_type="destination")

    if settings.strict_real_data:
        return []

    budget = intent.budget or 1000
    preferred = user.get("travel_style", []) + intent.constraints + intent.keywords
    items = []

    for destination in dataset["destinations"]:
        tags = set(destination.get("tags", []))
        preference = _tag_overlap_score(tags, preferred)
        health = 1.0 if "不太累" in preferred and "轻松" in tags else 0.7
        budget_score = _budget_score(destination.get("budget", 0), budget)
        dynamic_distance = _dynamic_distance(destination, intent)
        distance_km = dynamic_distance if dynamic_distance is not None else destination.get("distance_km", 300)
        distance = _distance_score(distance_km / 80)
        context = _tag_overlap_score(tags, intent.keywords + intent.constraints)
        score = _weighted_score(preference, health, budget_score, distance, context)
        reasons = [
            f"适合{destination['duration']}安排",
            f"预算约 {destination['budget']} 元，和你的预算匹配度较高",
            f"风格标签：{', '.join(destination['tags'][:3])}",
        ]
        items.append(_item(
            id=destination["id"],
            name=destination["city"],
            item_type="destination",
            score=score,
            tags=sorted(tags),
            reasons=reasons,
            suggested_items=destination.get("highlights", []),
            meta={
                "budget": destination["budget"],
                "duration": destination["duration"],
                "distance_km": round(distance_km, 2),
                "source": "dynamic-location" if dynamic_distance is not None else "sample-distance",
            },
            breakdown=(preference, health, budget_score, distance, context),
        ))

    return sorted(items, key=lambda item: item.score, reverse=True)


def _recommend_from_real_places(places: list[NearbyPlace], user: dict[str, Any], intent: ParsedIntent, health_tags: list[str], item_type: str) -> list[RecommendationItem]:
    budget = intent.budget or user.get("default_budget", 50)
    items: list[RecommendationItem] = []
    provider = get_place_provider()
    for index, place in enumerate(places):
        tags = set(place.tags)
        preference = _tag_overlap_score(tags, user.get("taste", []) + user.get("travel_style", []))
        health = _health_score(tags, health_tags) if health_tags else 0.7
        budget_score = 0.65 if budget else 0.5
        distance = _distance_score(place.distance_km or 5)
        context = _tag_overlap_score(tags.union({place.name, place.type}), intent.constraints + intent.keywords)
        score = _weighted_score(preference, health, budget_score, distance, context)
        suggested = _dish_guidance(health_tags) if item_type == "restaurant" else []
        route = _safe_route(provider, intent, place) if index < 5 else None
        reasons = [
            f"来自真实高德地点数据：{place.name}。",
            f"地址：{place.address or '高德暂未返回详细地址'}。",
        ]
        if place.distance_km is not None:
            reasons.append(f"距离当前位置约 {place.distance_km:.2f} 公里。")
        if route and route.distance_meters is not None:
            minutes = round((route.duration_seconds or 0) / 60)
            reasons.append(f"高德步行路线约 {route.distance_meters} 米，预计 {minutes} 分钟。")
        if suggested:
            reasons.append("菜品建议是健康选择原则，不代表该餐厅真实菜单。")
        meta: dict[str, Any] = {
            "address": place.address or "",
            "distance_km": place.distance_km or "",
            "latitude": place.latitude or "",
            "longitude": place.longitude or "",
            "source": place.source,
            "data_type": "real-poi",
        }
        if route:
            meta.update({
                "route_distance_meters": route.distance_meters or "",
                "route_duration_minutes": round((route.duration_seconds or 0) / 60) if route.duration_seconds else "",
                "route_source": route.source,
            })
        items.append(
            _item(
                id=place.id,
                name=place.name,
                item_type=item_type,
                score=score,
                tags=sorted(tags),
                reasons=reasons,
                suggested_items=suggested,
                meta=meta,
                breakdown=(preference, health, budget_score, distance, context),
            )
        )
    return sorted(items, key=lambda item: item.score, reverse=True)


def _select_dishes(dishes: list[dict[str, Any]], user: dict[str, Any], health_tags: list[str]) -> list[dict[str, Any]]:
    preferred = _preferred_health_tags(health_tags) + user.get("taste", [])
    avoid = set(user.get("allergies", []) + user.get("avoid", []))
    scored = []
    for dish in dishes:
        tags = set(dish.get("tags", []))
        if avoid.intersection(tags) or dish["name"] in avoid:
            continue
        score = _tag_overlap_score(tags, preferred) + _health_score(tags, health_tags)
        scored.append((score, dish))
    return [dish for _, dish in sorted(scored, key=lambda pair: pair[0], reverse=True)[:3]]


def _preferred_health_tags(health_tags: list[str]) -> list[str]:
    preferred: list[str] = []
    for tag in health_tags:
        preferred.extend(HEALTH_RULES.get(tag, {}).get("prefer", []))
    return preferred


def _tag_overlap_score(tags: set[str] | list[str], preferred: list[str]) -> float:
    if not preferred:
        return 0.6
    tag_set = set(tags)
    matched = sum(1 for tag in preferred if tag in tag_set)
    return min(1.0, 0.35 + matched / max(1, len(preferred)))


def _health_score(tags: set[str], health_tags: list[str]) -> float:
    preferred = _preferred_health_tags(health_tags)
    avoid = []
    for tag in health_tags:
        avoid.extend(HEALTH_RULES.get(tag, {}).get("avoid", []))
    score = 0.45 + 0.12 * sum(1 for tag in preferred if tag in tags)
    score -= 0.18 * sum(1 for tag in avoid if tag in tags)
    return _clamp(score)


def _budget_score(price: float, budget: float) -> float:
    if budget <= 0:
        return 0.5
    ratio = price / budget
    if ratio <= 1:
        return _clamp(1 - abs(0.75 - ratio) * 0.35)
    return _clamp(1 - (ratio - 1) * 0.75)


def _distance_score(distance_km: float) -> float:
    return _clamp(math.exp(-distance_km / 3))


def _weighted_score(preference: float, health: float, budget: float, distance: float, context: float) -> float:
    return round(
        100 * (
            0.25 * preference
            + 0.25 * health
            + 0.18 * budget
            + 0.17 * distance
            + 0.15 * context
        ),
        1,
    )


def _item(id: str, name: str, item_type: str, score: float, tags: list[str], reasons: list[str], breakdown: tuple[float, float, float, float, float], suggested_items: list[str] | None = None, meta: dict[str, Any] | None = None) -> RecommendationItem:
    return RecommendationItem(
        id=id,
        name=name,
        type=item_type,
        score=score,
        tags=tags,
        reasons=reasons,
        suggested_items=suggested_items or [],
        meta=meta or {},
        score_breakdown=ScoreBreakdown(
            preference=round(breakdown[0], 2),
            health=round(breakdown[1], 2),
            budget=round(breakdown[2], 2),
            distance=round(breakdown[3], 2),
            context=round(breakdown[4], 2),
        ),
    )


def _build_reasons(name: str, tags: set[str], health_tags: list[str], budget: float, distance: float) -> list[str]:
    reasons = []
    preferred = [tag for tag in _preferred_health_tags(health_tags) if tag in tags]
    if preferred:
        reasons.append(f"{name} 的标签包含 {', '.join(preferred[:3])}，能修正近期饮食状态。")
    if budget > 0.75:
        reasons.append("价格与当前预算匹配。")
    if distance > 0.65:
        reasons.append("距离较近，适合临时决定外出用餐。")
    if not reasons:
        reasons.append("综合口味、预算和场景后排名靠前。")
    return reasons


def _build_food_plan(items: list[RecommendationItem], health_tags: list[str], weather_context: dict[str, str | int | float | None]) -> list[str]:
    top = items[0] if items else None
    preferred = _preferred_health_tags(health_tags)
    plan = [
        f"今日饮食方向：优先选择{', '.join(preferred[:3]) or '均衡、不过量'}。",
    ]
    weather_note = _weather_plan_note(weather_context)
    if weather_note:
        plan.append(weather_note)
    if not top:
        plan.append("未获得真实餐厅 POI，请确认已配置高德 Key，并在请求中提供经纬度或城市。")
        return plan
    if top:
        plan.append(f"首选餐厅：{top.name}，建议点 {', '.join(top.suggested_items[:2])}。")
        plan.append("如果仍然没胃口，选择小份主食 + 蛋白质 + 蔬菜的组合，避免重油重辣。")
    return plan


def _build_shopping_plan(items: list[RecommendationItem], weather_context: dict[str, str | int | float | None]) -> list[str]:
    if not items:
        return ["未获得 AIGC 商品建议，请确认 LLM API 已配置并可用。"]
    names = [item.name for item in items[:4]]
    plan = [
        "先买能降低执行成本的基础食材和工具。",
        f"建议清单：{', '.join(names)}。",
        "优先选择能保存、易加工、适合多餐复用的商品。",
    ]
    weather_note = _weather_plan_note(weather_context)
    if weather_note:
        plan.append(weather_note)
    return plan


def _build_travel_plan(items: list[RecommendationItem], intent: ParsedIntent, weather_context: dict[str, str | int | float | None]) -> list[str]:
    if not items:
        return ["暂时没有匹配目的地，可以放宽预算或时间限制。"]
    top = items[0]
    highlights = top.suggested_items[:3]
    plan = [
        f"推荐目的地：{top.name}，适合 {top.meta.get('duration', '短途')}。",
        f"第一阶段：抵达后安排 {highlights[0] if highlights else '轻量景点'}，减少奔波。",
        f"第二阶段：围绕 {', '.join(highlights[1:]) if len(highlights) > 1 else '本地餐饮'} 做半日规划。",
        "保留 20% 时间作为机动，避免行程过满。",
    ]
    weather_note = _weather_plan_note(weather_context)
    if weather_note:
        plan.insert(1, weather_note)
    return plan


def _health_summary(health_tags: list[str]) -> str:
    if not health_tags:
        return "近期饮食状态较均衡。"
    return f"近期需要关注：{', '.join(health_tags)}。建议选择 {', '.join(_preferred_health_tags(health_tags)[:4])}。"


def _strategy_summary(scenario: str, health_tags: list[str]) -> str:
    if scenario == "travel":
        return "采用目的地标签匹配、预算约束和轻量行程生成。"
    if scenario == "shopping":
        return "采用生活场景候选生成、预算过滤和健康目标匹配。"
    return f"采用健康约束优先的餐厅与菜品排序，当前健康标签为：{', '.join(health_tags) or '无明显风险'}。"


def _context_summary(intent: ParsedIntent, weather_context: dict[str, str | int | float | None]) -> dict[str, str | float | int | bool | None]:
    context: dict[str, str | float | int | bool | None] = {
        "location": intent.location,
        "latitude": intent.latitude,
        "longitude": intent.longitude,
        "radius_km": intent.radius_km,
        "dynamic_location_enabled": intent.latitude is not None and intent.longitude is not None,
        "strict_real_data": settings.strict_real_data,
        "data_source_policy": "real-provider-only" if settings.strict_real_data else "real-provider-with-dev-fallback",
    }
    context.update(weather_context)
    return context


def _intent_summary(intent: ParsedIntent) -> str:
    parts = [f"识别场景：{intent.scenario}"]
    if intent.location:
        parts.append(f"地点：{intent.location}")
    if intent.budget:
        parts.append(f"预算：{intent.budget:g} 元")
    if intent.constraints:
        parts.append(f"约束：{', '.join(intent.constraints)}")
    return "；".join(parts)


def _dynamic_distance(entity: dict[str, Any], intent: ParsedIntent) -> float | None:
    if intent.latitude is None or intent.longitude is None:
        return None
    lat = entity.get("latitude")
    lon = entity.get("longitude")
    if lat is None or lon is None:
        return None
    return haversine_km(intent.latitude, intent.longitude, lat, lon)


def _should_use_real_places(intent: ParsedIntent) -> bool:
    return bool(settings.amap_api_key and intent.latitude is not None and intent.longitude is not None)


def _safe_places(loader: Any) -> list[NearbyPlace]:
    try:
        return loader()
    except Exception:
        return []


def _safe_route(provider: Any, intent: ParsedIntent, place: NearbyPlace) -> RouteResponse | None:
    if intent.latitude is None or intent.longitude is None or place.latitude is None or place.longitude is None:
        return None
    try:
        route = provider.walking_route(
            origin_latitude=intent.latitude,
            origin_longitude=intent.longitude,
            destination_latitude=place.latitude,
            destination_longitude=place.longitude,
        )
    except Exception:
        return None
    if route.source != "amap":
        return None
    return route


def _load_weather_context(intent: ParsedIntent) -> dict[str, str | int | float | None]:
    provider = get_place_provider()
    weather: WeatherResponse | None = None
    try:
        if intent.latitude is not None and intent.longitude is not None:
            location = provider.reverse_geocode(latitude=intent.latitude, longitude=intent.longitude)
            weather = provider.weather(city=location.city, adcode=location.adcode)
        elif intent.location:
            weather = provider.weather(city=intent.location)
    except Exception:
        return {"weather_source": "unavailable"}

    if not weather:
        return {"weather_source": "missing-location"}
    return {
        "weather_source": weather.source,
        "weather_city": weather.city,
        "weather": weather.weather,
        "temperature": weather.temperature,
        "humidity": weather.humidity,
        "weather_report_time": weather.report_time,
    }


def _weather_plan_note(weather_context: dict[str, str | int | float | None]) -> str | None:
    weather = str(weather_context.get("weather") or "")
    temperature_text = weather_context.get("temperature")
    if not weather:
        return None
    if any(word in weather for word in ["雨", "雪", "雾", "霾"]):
        return f"天气为{weather}，优先选择步行距离短、室内为主的方案。"
    try:
        temperature = float(str(temperature_text))
    except (TypeError, ValueError):
        temperature = None
    if temperature is not None and temperature >= 30:
        return f"当前约 {temperature:g}℃，建议减少暴晒和长时间步行，饮食上补水、少油。"
    if temperature is not None and temperature <= 5:
        return f"当前约 {temperature:g}℃，建议选择室内或交通便利地点，饮食上偏温热。"
    return f"当前天气{weather}，可按正常节奏安排。"


def _apply_feedback_profile(items: list[RecommendationItem], profile: dict[str, Any]) -> list[RecommendationItem]:
    if not items:
        return items

    positive = profile.get("positive", {})
    negative = profile.get("negative", {})
    positive_items = positive.get("items", {})
    positive_tags = positive.get("tags", {})
    negative_items = negative.get("items", {})
    negative_tags = negative.get("tags", {})

    adjusted: list[RecommendationItem] = []
    for item in items:
        delta = 0.0
        delta += min(8.0, 4.0 * positive_items.get(item.name, 0))
        delta -= min(12.0, 6.0 * negative_items.get(item.name, 0))
        for tag in item.tags:
            delta += min(3.0, 0.8 * positive_tags.get(tag, 0))
            delta -= min(4.0, 1.0 * negative_tags.get(tag, 0))
        if delta:
            item.score = round(_clamp_score(item.score + delta), 1)
            item.meta["feedback_adjustment"] = round(delta, 1)
            item.reasons.append("已参考你之前的喜欢/不喜欢/加入计划反馈进行重排。")
        adjusted.append(item)
    return sorted(adjusted, key=lambda candidate: candidate.score, reverse=True)


def _exclude_items(items: list[RecommendationItem], item_ids: list[str], item_names: list[str]) -> list[RecommendationItem]:
    excluded_ids = {str(item_id) for item_id in item_ids}
    excluded_names = {str(item_name) for item_name in item_names}
    return [
        item
        for item in items
        if item.id not in excluded_ids and item.name not in excluded_names
    ]


def _request_payload(**kwargs: Any) -> dict[str, Any]:
    return kwargs


def _build_user_profile(
    base_user: dict[str, Any],
    budget: float | None,
    taste: list[str],
    avoid: list[str],
    allergies: list[str],
    health_goals: list[str],
    recent_meal_tags: list[str],
    travel_style: list[str],
) -> dict[str, Any]:
    if settings.strict_real_data:
        user: dict[str, Any] = {
            "id": base_user.get("id", "runtime"),
            "default_location": None,
            "default_budget": budget or 50,
            "taste": taste,
            "avoid": avoid,
            "allergies": allergies,
            "health_goals": health_goals,
            "travel_style": travel_style,
            "recent_meals": [{"tags": recent_meal_tags}] if recent_meal_tags else [],
        }
        return user

    user = dict(base_user)
    if taste:
        user["taste"] = taste
    if avoid:
        user["avoid"] = avoid
    if allergies:
        user["allergies"] = allergies
    if health_goals:
        user["health_goals"] = health_goals
    if travel_style:
        user["travel_style"] = travel_style
    if budget:
        user["default_budget"] = budget
    if recent_meal_tags:
        user["recent_meals"] = [{"tags": recent_meal_tags}]
    return user


def _dish_guidance(health_tags: list[str]) -> list[str]:
    preferred = _preferred_health_tags(health_tags)
    if preferred:
        return [f"优先选择{tag}相关菜品" for tag in preferred[:3]]
    return ["优先选择少油少盐", "搭配蔬菜和蛋白质", "避免过量甜饮和油炸"]


def _follow_ups(scenario: str) -> list[str]:
    if scenario == "travel":
        return ["你希望更轻松还是更充实？", "是否需要加入餐厅和购物清单？"]
    if scenario == "shopping":
        return ["你更想低预算还是高品质？", "是否要按一周饮食计划生成清单？"]
    return ["你想堂食、外卖还是自己做？", "是否需要避开辣、甜或油炸？"]


def _find_user(users: list[dict[str, Any]], user_id: str) -> dict[str, Any]:
    return next((user for user in users if user["id"] == user_id), users[0])


def _extract_budget(message: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(元|块|预算)?", message)
    if match:
        return float(match.group(1))
    return None


def _extract_location(message: str) -> str | None:
    for marker in ["南京", "学校", "江宁", "上海", "杭州", "北京"]:
        if marker in message:
            return marker
    return None


def _tokenize(message: str) -> list[str]:
    return [word for word in re.split(r"[\s,，。！？]+", message) if word]


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, value))
