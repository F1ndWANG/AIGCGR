from typing import Literal

from pydantic import BaseModel, Field


Scenario = Literal["auto", "diet", "restaurant", "shopping", "travel"]
ProductProviderName = Literal["auto", "aigc", "local"]
FeedbackAction = Literal["like", "dislike", "save", "plan", "skip"]
PlanStatus = Literal["active", "done", "canceled"]


class RecommendationRequest(BaseModel):
    message: str = Field(..., min_length=1)
    scenario: Scenario = "auto"
    user_id: str = "u001"
    location: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_km: float = Field(default=3.0, gt=0, le=50)
    budget: float | None = None
    taste: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    health_goals: list[str] = Field(default_factory=list)
    recent_meal_tags: list[str] = Field(default_factory=list)
    recent_wellness_tags: list[str] = Field(default_factory=list)
    travel_style: list[str] = Field(default_factory=list)
    exclude_item_ids: list[str] = Field(default_factory=list)
    exclude_item_names: list[str] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    preference: float
    health: float
    budget: float
    distance: float
    context: float


class RecommendationItem(BaseModel):
    id: str
    name: str
    type: str
    score: float
    tags: list[str]
    reasons: list[str]
    suggested_items: list[str] = []
    meta: dict[str, str | float | int] = {}
    score_breakdown: ScoreBreakdown


class RecommendationResponse(BaseModel):
    request_id: str
    scenario: str
    intent_summary: str
    health_summary: str
    strategy: str
    context: dict[str, str | float | int | bool | None] = {}
    aigc_summary: str | None = None
    recommendations: list[RecommendationItem]
    plan: list[str]
    follow_up_questions: list[str]
    safety_note: str


class RecommendationHistoryTopItem(BaseModel):
    id: str
    name: str
    type: str
    score: float | None = None
    tags: list[str] = []
    source: str | None = None


class RecommendationHistoryItem(BaseModel):
    request_id: str
    scenario: str
    message: str
    created_at: str
    context: dict[str, str | float | int | bool | None] = {}
    item_count: int
    top_items: list[RecommendationHistoryTopItem]


class RecommendationHistoryResponse(BaseModel):
    user_id: str
    recommendations: list[RecommendationHistoryItem]


class NearbyRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    keyword: str = "餐厅"
    radius_km: float = Field(default=3.0, gt=0, le=50)


class NearbyPlace(BaseModel):
    id: str
    name: str
    type: str
    latitude: float | None = None
    longitude: float | None = None
    distance_km: float | None = None
    address: str | None = None
    tags: list[str] = []
    source: str


class NearbyResponse(BaseModel):
    provider: str
    places: list[NearbyPlace]


class PlaceSearchRequest(BaseModel):
    keyword: str = "景点"
    city: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


class ReverseGeocodeResponse(BaseModel):
    provider: str
    formatted_address: str | None = None
    country: str | None = None
    province: str | None = None
    city: str | None = None
    district: str | None = None
    adcode: str | None = None
    source: str = "unknown"


class WeatherResponse(BaseModel):
    provider: str
    city: str | None = None
    adcode: str | None = None
    weather: str | None = None
    temperature: str | None = None
    wind_direction: str | None = None
    wind_power: str | None = None
    humidity: str | None = None
    report_time: str | None = None
    source: str


class RouteRequest(BaseModel):
    origin_latitude: float = Field(..., ge=-90, le=90)
    origin_longitude: float = Field(..., ge=-180, le=180)
    destination_latitude: float = Field(..., ge=-90, le=90)
    destination_longitude: float = Field(..., ge=-180, le=180)


class RouteResponse(BaseModel):
    provider: str
    distance_meters: int | None = None
    duration_seconds: int | None = None
    steps: list[str] = []
    source: str


class AigcBriefRequest(BaseModel):
    message: str
    scenario: Scenario = "auto"
    health_tags: list[str] = Field(default_factory=list)


class AigcBriefResponse(BaseModel):
    provider: str
    summary: str
    prompt_slot: str


class DailyBriefResponse(BaseModel):
    user_id: str
    provider: str
    generated_at: str
    summary: str
    priorities: list[str]
    risk_flags: list[str]
    next_actions: list[str]
    context_sources: dict[str, str]


class ProductSearchRequest(BaseModel):
    keyword: str = "健康饮食"
    provider: ProductProviderName = "auto"
    budget: float | None = None
    tags: list[str] = Field(default_factory=list)
    scenario: str = "shopping"
    limit: int = Field(default=10, ge=1, le=50)


class ProductItem(BaseModel):
    id: str
    name: str
    provider: str
    category: str | None = None
    price: float | None = None
    tags: list[str] = []
    url: str | None = None
    reason: str | None = None
    purchase_hint: str | None = None
    source: str


class ProductSearchResponse(BaseModel):
    provider: str
    products: list[ProductItem]
    note: str


class FeedbackRequest(BaseModel):
    user_id: str = "u001"
    request_id: str | None = None
    item_id: str
    item_name: str
    item_type: str
    action: FeedbackAction
    tags: list[str] = Field(default_factory=list)
    source: str | None = None
    reason: str | None = None


class FeedbackResponse(BaseModel):
    id: int
    status: str
    action: FeedbackAction
    message: str


class FeedbackSummaryResponse(BaseModel):
    user_id: str
    positive: dict[str, dict[str, int]]
    negative: dict[str, dict[str, int]]
    events: list[dict[str, str | list[str] | None]]


class MealLogRequest(BaseModel):
    user_id: str = "u001"
    meal_name: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)
    note: str | None = None
    meal_time: str | None = None


class MealEvent(BaseModel):
    id: int
    user_id: str
    meal_name: str
    tags: list[str]
    note: str | None = None
    meal_time: str | None = None
    created_at: str


class MealLogResponse(BaseModel):
    id: int
    status: str
    message: str
    recent_meal_tags: list[str]


class MealHistoryResponse(BaseModel):
    user_id: str
    recent_meal_tags: list[str]
    meals: list[MealEvent]


class WellnessLogRequest(BaseModel):
    user_id: str = "u001"
    tags: list[str] = Field(default_factory=list)
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    exercise_minutes: int | None = Field(default=None, ge=0, le=1440)
    stress_level: int | None = Field(default=None, ge=1, le=5)
    mood: str | None = None
    note: str | None = None
    event_time: str | None = None


class WellnessEvent(BaseModel):
    id: int
    user_id: str
    tags: list[str]
    sleep_hours: float | None = None
    exercise_minutes: int | None = None
    stress_level: int | None = None
    mood: str | None = None
    note: str | None = None
    event_time: str | None = None
    created_at: str


class WellnessLogResponse(BaseModel):
    id: int
    status: str
    message: str
    recent_wellness_tags: list[str]


class WellnessHistoryResponse(BaseModel):
    user_id: str
    recent_wellness_tags: list[str]
    wellness: list[WellnessEvent]


class UserPreferencesRequest(BaseModel):
    user_id: str = "u001"
    default_location: str | None = None
    default_budget: float | None = Field(default=None, gt=0)
    taste: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    health_goals: list[str] = Field(default_factory=list)
    travel_style: list[str] = Field(default_factory=list)


class UserPreferencesResponse(UserPreferencesRequest):
    updated_at: str | None = None


class PlanItemRequest(BaseModel):
    user_id: str = "u001"
    request_id: str | None = None
    item_id: str
    item_name: str
    item_type: str
    title: str | None = None
    tags: list[str] = Field(default_factory=list)
    source: str | None = None
    note: str | None = None
    scheduled_for: str | None = None


class PlanItemResponse(PlanItemRequest):
    id: int
    status: PlanStatus
    created_at: str
    updated_at: str


class PlanListResponse(BaseModel):
    user_id: str
    plans: list[PlanItemResponse]


class PlanExportResponse(BaseModel):
    user_id: str
    generated_at: str
    summary: dict[str, int]
    active: list[PlanItemResponse]
    done: list[PlanItemResponse]
    canceled: list[PlanItemResponse]


class PlanStatusUpdateRequest(BaseModel):
    user_id: str = "u001"
    status: PlanStatus | None = None
    title: str | None = None
    note: str | None = None
    scheduled_for: str | None = None


class UserContextResponse(BaseModel):
    user_id: str
    recent_meal_tags: list[str]
    recent_wellness_tags: list[str]
    recent_recommendations: list[RecommendationHistoryItem]
    meals: list[MealEvent]
    wellness: list[WellnessEvent]
    feedback: FeedbackSummaryResponse
    preferences: UserPreferencesResponse
    plans: list[PlanItemResponse]
    storage: dict[str, str | int]
    context_sources: dict[str, str]


class RefreshRecommendationRequest(BaseModel):
    request_id: str
    user_id: str = "u001"
    exclude_item_ids: list[str] = Field(default_factory=list)
    exclude_item_names: list[str] = Field(default_factory=list)
