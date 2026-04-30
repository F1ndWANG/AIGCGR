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
    ProductSearchRequest,
    ProductSearchResponse,
    RefreshRecommendationRequest,
    RecommendationRequest,
    RecommendationResponse,
    ReverseGeocodeResponse,
    RouteRequest,
    RouteResponse,
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
    recent_meal_tags,
    save_feedback_event,
    save_meal_event,
    storage_status,
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
        travel_style=refreshed_payload.get("travel_style", []),
        exclude_item_ids=refreshed_payload["exclude_item_ids"],
        exclude_item_names=refreshed_payload["exclude_item_names"],
        request_payload=refreshed_payload,
    )
