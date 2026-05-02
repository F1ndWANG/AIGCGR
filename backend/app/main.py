from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .aigc import build_life_brief
from .data_loader import load_dataset
from .models import (
    AigcBriefRequest,
    AigcBriefResponse,
    FeedbackRequest,
    FeedbackResponse,
    FeedbackSummaryResponse,
    MealHistoryResponse,
    MealLogRequest,
    MealLogResponse,
    NearbyRequest,
    NearbyResponse,
    PlaceSearchRequest,
    PlanItemRequest,
    PlanItemResponse,
    PlanListResponse,
    PlanStatusUpdateRequest,
    ProductSearchRequest,
    ProductSearchResponse,
    RefreshRecommendationRequest,
    RecommendationRequest,
    RecommendationResponse,
    ReverseGeocodeResponse,
    RouteRequest,
    RouteResponse,
    UserContextResponse,
    UserPreferencesRequest,
    UserPreferencesResponse,
    WellnessHistoryResponse,
    WellnessLogRequest,
    WellnessLogResponse,
    WeatherResponse,
)
from .product_providers import get_product_provider, product_provider_status
from .providers import get_place_provider, provider_capabilities
from .recommender import recommend
from .storage import (
    feedback_summary,
    get_recommendation_event,
    init_storage,
    meal_history,
    plan_items,
    recent_meal_tags,
    save_feedback_event,
    save_meal_event,
    save_plan_item,
    save_user_preferences,
    storage_status,
    update_plan_item_status,
    user_preferences,
    recent_wellness_tags,
    save_wellness_event,
    wellness_history,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_storage()
    yield


app = FastAPI(
    title="LifeRec API",
    description="AIGC 与生成式推荐结合的 AI 生活推荐系统后端。",
    version="0.2.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "version": app.version,
        "storage": storage_status(),
    }


@app.get("/api/dataset/summary")
def dataset_summary() -> dict[str, int]:
    dataset = load_dataset()
    return {key: len(value) for key, value in dataset.items()}


@app.get("/api/providers/capabilities")
def capabilities() -> dict[str, dict[str, bool | str] | dict[str, dict[str, bool | str]]]:
    data: dict[str, dict[str, bool | str] | dict[str, dict[str, bool | str]]] = provider_capabilities()
    data["product_providers"] = product_provider_status()
    return data


@app.post("/api/context/nearby", response_model=NearbyResponse)
def nearby_places(request: NearbyRequest) -> NearbyResponse:
    provider = get_place_provider()
    places = provider.nearby(
        latitude=request.latitude,
        longitude=request.longitude,
        keyword=request.keyword,
        radius_km=request.radius_km,
    )
    return NearbyResponse(provider=provider.name, places=places)


@app.post("/api/context/places/search", response_model=NearbyResponse)
def search_places(request: PlaceSearchRequest) -> NearbyResponse:
    provider = get_place_provider()
    places = provider.text_search(
        keyword=request.keyword,
        city=request.city,
        limit=request.limit,
    )
    return NearbyResponse(provider=provider.name, places=places)


@app.get("/api/context/geocode/reverse", response_model=ReverseGeocodeResponse)
def reverse_geocode(latitude: float, longitude: float) -> ReverseGeocodeResponse:
    provider = get_place_provider()
    return provider.reverse_geocode(latitude=latitude, longitude=longitude)


@app.post("/api/context/products/search", response_model=ProductSearchResponse)
def search_products(request: ProductSearchRequest) -> ProductSearchResponse:
    provider = get_product_provider(request.provider)
    products = provider.search(
        keyword=request.keyword,
        budget=request.budget,
        tags=request.tags,
        limit=request.limit,
        scenario=request.scenario,
    )
    return ProductSearchResponse(
        provider=provider.name,
        products=products,
        note="当前商品能力采用 AIGC 生成商品需求清单，不依赖淘宝、京东或拼多多；不会声称实时 SKU、库存、折扣或购买链接。",
    )


@app.get("/api/context/weather", response_model=WeatherResponse)
def weather(latitude: float | None = None, longitude: float | None = None, city: str | None = None, adcode: str | None = None) -> WeatherResponse:
    provider = get_place_provider()
    if adcode or city:
        return provider.weather(city=city, adcode=adcode)
    if latitude is not None and longitude is not None:
        location = provider.reverse_geocode(latitude=latitude, longitude=longitude)
        return provider.weather(city=location.city, adcode=location.adcode)
    return WeatherResponse(provider=provider.name, source="missing-location")


@app.post("/api/context/route/walking", response_model=RouteResponse)
def walking_route(request: RouteRequest) -> RouteResponse:
    provider = get_place_provider()
    return provider.walking_route(
        origin_latitude=request.origin_latitude,
        origin_longitude=request.origin_longitude,
        destination_latitude=request.destination_latitude,
        destination_longitude=request.destination_longitude,
    )


@app.post("/api/aigc/brief", response_model=AigcBriefResponse)
def aigc_brief(request: AigcBriefRequest) -> AigcBriefResponse:
    summary, prompt_slot = build_life_brief(
        message=request.message,
        scenario=request.scenario,
        health_tags=request.health_tags,
    )
    return AigcBriefResponse(
        provider="llm" if provider_capabilities()["aigc"]["active"] else "template-generator",
        summary=summary,
        prompt_slot=prompt_slot,
    )


@app.post("/api/feedback", response_model=FeedbackResponse)
def create_feedback(request: FeedbackRequest) -> FeedbackResponse:
    feedback_id = save_feedback_event(
        request_id=request.request_id,
        user_id=request.user_id,
        item_id=request.item_id,
        item_name=request.item_name,
        item_type=request.item_type,
        action=request.action,
        reason=request.reason,
        tags=request.tags,
        source=request.source,
    )
    return FeedbackResponse(
        id=feedback_id,
        status="ok",
        action=request.action,
        message="反馈已保存，后续推荐会参考该偏好。",
    )


@app.get("/api/feedback/summary", response_model=FeedbackSummaryResponse)
def get_feedback_summary(user_id: str = "u001") -> FeedbackSummaryResponse:
    return FeedbackSummaryResponse(**feedback_summary(user_id=user_id))


@app.post("/api/user/meals", response_model=MealLogResponse)
def create_meal_log(request: MealLogRequest) -> MealLogResponse:
    meal_id = save_meal_event(
        user_id=request.user_id,
        meal_name=request.meal_name,
        tags=request.tags,
        note=request.note,
        meal_time=request.meal_time,
    )
    return MealLogResponse(
        id=meal_id,
        status="ok",
        message="饮食记录已保存，后续推荐会优先参考这些真实生活状态。",
        recent_meal_tags=recent_meal_tags(user_id=request.user_id),
    )


@app.get("/api/user/meals", response_model=MealHistoryResponse)
def get_meal_logs(user_id: str = "u001", limit: int = 20) -> MealHistoryResponse:
    safe_limit = max(1, min(limit, 100))
    return MealHistoryResponse(
        user_id=user_id,
        recent_meal_tags=recent_meal_tags(user_id=user_id, limit=safe_limit),
        meals=meal_history(user_id=user_id, limit=safe_limit),
    )


@app.post("/api/user/wellness", response_model=WellnessLogResponse)
def create_wellness_log(request: WellnessLogRequest) -> WellnessLogResponse:
    wellness_id = save_wellness_event(
        user_id=request.user_id,
        tags=request.tags,
        sleep_hours=request.sleep_hours,
        exercise_minutes=request.exercise_minutes,
        stress_level=request.stress_level,
        mood=request.mood,
        note=request.note,
        event_time=request.event_time,
    )
    return WellnessLogResponse(
        id=wellness_id,
        status="ok",
        message="生活状态已保存，后续推荐会参考这些非医疗生活信号。",
        recent_wellness_tags=recent_wellness_tags(user_id=request.user_id),
    )


@app.get("/api/user/wellness", response_model=WellnessHistoryResponse)
def get_wellness_logs(user_id: str = "u001", limit: int = 20) -> WellnessHistoryResponse:
    safe_limit = max(1, min(limit, 100))
    return WellnessHistoryResponse(
        user_id=user_id,
        recent_wellness_tags=recent_wellness_tags(user_id=user_id, limit=safe_limit),
        wellness=wellness_history(user_id=user_id, limit=safe_limit),
    )


@app.get("/api/user/context", response_model=UserContextResponse)
def get_user_context(user_id: str = "u001", limit: int = 20) -> UserContextResponse:
    safe_limit = max(1, min(limit, 100))
    feedback = FeedbackSummaryResponse(**feedback_summary(user_id=user_id))
    meals = meal_history(user_id=user_id, limit=safe_limit)
    tags = recent_meal_tags(user_id=user_id, limit=safe_limit)
    wellness = wellness_history(user_id=user_id, limit=safe_limit)
    wellness_tags = recent_wellness_tags(user_id=user_id, limit=safe_limit)
    preferences = UserPreferencesResponse(**user_preferences(user_id=user_id))
    plans = [PlanItemResponse(**item) for item in plan_items(user_id=user_id, status="active", limit=10)]
    return UserContextResponse(
        user_id=user_id,
        recent_meal_tags=tags,
        recent_wellness_tags=wellness_tags,
        meals=meals,
        wellness=wellness,
        feedback=feedback,
        preferences=preferences,
        plans=plans,
        storage=storage_status(),
        context_sources={
            "meals": "runtime.sqlite.meal_events",
            "wellness": "runtime.sqlite.wellness_events",
            "feedback": "runtime.sqlite.feedback_events",
            "recommendations": "runtime.sqlite.recommendation_events",
            "provider_cache": "runtime.sqlite.api_cache",
            "preferences": "runtime.sqlite.user_preferences",
            "plans": "runtime.sqlite.plan_items",
        },
    )


@app.get("/api/user/preferences", response_model=UserPreferencesResponse)
def get_preferences(user_id: str = "u001") -> UserPreferencesResponse:
    return UserPreferencesResponse(**user_preferences(user_id=user_id))


@app.put("/api/user/preferences", response_model=UserPreferencesResponse)
def update_preferences(request: UserPreferencesRequest) -> UserPreferencesResponse:
    saved = save_user_preferences(
        user_id=request.user_id,
        default_location=request.default_location,
        default_budget=request.default_budget,
        taste=request.taste,
        avoid=request.avoid,
        allergies=request.allergies,
        health_goals=request.health_goals,
        travel_style=request.travel_style,
    )
    return UserPreferencesResponse(**saved)


@app.post("/api/user/plans", response_model=PlanItemResponse)
def create_plan_item(request: PlanItemRequest) -> PlanItemResponse:
    saved = save_plan_item(
        user_id=request.user_id,
        request_id=request.request_id,
        item_id=request.item_id,
        item_name=request.item_name,
        item_type=request.item_type,
        title=request.title,
        tags=request.tags,
        source=request.source,
        note=request.note,
        scheduled_for=request.scheduled_for,
    )
    return PlanItemResponse(**saved)


@app.get("/api/user/plans", response_model=PlanListResponse)
def get_plan_items(user_id: str = "u001", status: str | None = "active", limit: int = 50) -> PlanListResponse:
    safe_limit = max(1, min(limit, 200))
    normalized_status = status if status in {"active", "done", "canceled"} else None
    items = [PlanItemResponse(**item) for item in plan_items(user_id=user_id, status=normalized_status, limit=safe_limit)]
    return PlanListResponse(user_id=user_id, plans=items)


@app.patch("/api/user/plans/{plan_id}", response_model=PlanItemResponse)
def update_plan_status(plan_id: int, request: PlanStatusUpdateRequest) -> PlanItemResponse:
    updated = update_plan_item_status(plan_id=plan_id, user_id=request.user_id, status=request.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Plan item not found")
    return PlanItemResponse(**updated)


@app.post("/api/recommend", response_model=RecommendationResponse)
def create_recommendation(request: RecommendationRequest) -> RecommendationResponse:
    return recommend(
        message=request.message,
        scenario=request.scenario,
        user_id=request.user_id,
        location=request.location,
        latitude=request.latitude,
        longitude=request.longitude,
        radius_km=request.radius_km,
        budget=request.budget,
        taste=request.taste,
        avoid=request.avoid,
        allergies=request.allergies,
        health_goals=request.health_goals,
        recent_meal_tags=request.recent_meal_tags,
        recent_wellness_tags=request.recent_wellness_tags,
        travel_style=request.travel_style,
        exclude_item_ids=request.exclude_item_ids,
        exclude_item_names=request.exclude_item_names,
        request_payload=request.model_dump(),
    )


@app.post("/api/recommend/refresh", response_model=RecommendationResponse)
def refresh_recommendation(request: RefreshRecommendationRequest) -> RecommendationResponse:
    event = get_recommendation_event(request.request_id)
    if not event:
        raise HTTPException(status_code=404, detail="Recommendation request_id not found")

    original = event.get("request") or {}
    if not original:
        context = event.get("context") or {}
        original = {
            "message": event["message"],
            "scenario": event["scenario"],
            "user_id": event["user_id"],
            "location": context.get("location"),
            "latitude": context.get("latitude"),
            "longitude": context.get("longitude"),
            "radius_km": context.get("radius_km", 3.0),
        }
    previous_items = event.get("recommendations") or []
    exclude_item_ids = {
        str(item.get("id"))
        for item in previous_items
        if item.get("id") is not None
    }
    exclude_item_names = {
        str(item.get("name"))
        for item in previous_items
        if item.get("name") is not None
    }
    exclude_item_ids.update(request.exclude_item_ids)
    exclude_item_names.update(request.exclude_item_names)

    refreshed_payload = {
        **original,
        "user_id": request.user_id or original.get("user_id", event["user_id"]),
        "exclude_item_ids": sorted(exclude_item_ids),
        "exclude_item_names": sorted(exclude_item_names),
    }
    return recommend(
        message=str(refreshed_payload.get("message") or event["message"]),
        scenario=refreshed_payload.get("scenario", event["scenario"]),
        user_id=refreshed_payload.get("user_id", event["user_id"]),
        location=refreshed_payload.get("location"),
        latitude=refreshed_payload.get("latitude"),
        longitude=refreshed_payload.get("longitude"),
        radius_km=refreshed_payload.get("radius_km", 3.0),
        budget=refreshed_payload.get("budget"),
        taste=refreshed_payload.get("taste", []),
        avoid=refreshed_payload.get("avoid", []),
        allergies=refreshed_payload.get("allergies", []),
        health_goals=refreshed_payload.get("health_goals", []),
        recent_meal_tags=refreshed_payload.get("recent_meal_tags", []),
        recent_wellness_tags=refreshed_payload.get("recent_wellness_tags", []),
        travel_style=refreshed_payload.get("travel_style", []),
        exclude_item_ids=refreshed_payload["exclude_item_ids"],
        exclude_item_names=refreshed_payload["exclude_item_names"],
        request_payload=refreshed_payload,
    )
