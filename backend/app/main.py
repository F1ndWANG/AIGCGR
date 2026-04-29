from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .aigc import build_life_brief
from .data_loader import load_dataset
from .models import (
    AigcBriefRequest,
    AigcBriefResponse,
    FeedbackRequest,
    FeedbackResponse,
    FeedbackSummaryResponse,
    NearbyRequest,
    NearbyResponse,
    PlaceSearchRequest,
    ProductSearchRequest,
    ProductSearchResponse,
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
from .storage import feedback_summary, init_storage, save_feedback_event


app = FastAPI(
    title="LifeRec API",
    description="AIGC 与生成式推荐结合的 AI 生活推荐系统后端。",
    version="0.1.0",
)


@app.on_event("startup")
def startup() -> None:
    init_storage()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
    )
