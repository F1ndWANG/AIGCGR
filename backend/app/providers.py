from __future__ import annotations

from typing import Any, Protocol

import httpx

from .config import settings
from .data_loader import load_dataset
from .geo import haversine_km
from .models import NearbyPlace, ReverseGeocodeResponse, RouteResponse, WeatherResponse


class PlaceProvider(Protocol):
    name: str

    def nearby(self, latitude: float, longitude: float, keyword: str, radius_km: float) -> list[NearbyPlace]:
        ...

    def text_search(self, keyword: str, city: str | None, limit: int) -> list[NearbyPlace]:
        ...

    def reverse_geocode(self, latitude: float, longitude: float) -> ReverseGeocodeResponse:
        ...

    def weather(self, city: str | None = None, adcode: str | None = None) -> WeatherResponse:
        ...

    def walking_route(self, origin_latitude: float, origin_longitude: float, destination_latitude: float, destination_longitude: float) -> RouteResponse:
        ...


class LocalPlaceProvider:
    name = "local-json"

    def nearby(self, latitude: float, longitude: float, keyword: str, radius_km: float) -> list[NearbyPlace]:
        dataset = load_dataset()
        places: list[NearbyPlace] = []
        for restaurant in dataset["restaurants"]:
            lat = restaurant.get("latitude")
            lon = restaurant.get("longitude")
            distance = None
            if lat is not None and lon is not None:
                distance = haversine_km(latitude, longitude, lat, lon)
                if distance > radius_km:
                    continue
            places.append(
                NearbyPlace(
                    id=restaurant["id"],
                    name=restaurant["name"],
                    type="restaurant",
                    latitude=lat,
                    longitude=lon,
                    distance_km=round(distance, 2) if distance is not None else restaurant.get("distance_km"),
                    address=restaurant.get("location"),
                    tags=restaurant.get("tags", []),
                    source=self.name,
                )
            )
        return sorted(places, key=lambda place: place.distance_km or 999)

    def text_search(self, keyword: str, city: str | None, limit: int) -> list[NearbyPlace]:
        dataset = load_dataset()
        places: list[NearbyPlace] = []
        for destination in dataset["destinations"][:limit]:
            places.append(
                NearbyPlace(
                    id=destination["id"],
                    name=destination["city"],
                    type="destination",
                    latitude=destination.get("latitude"),
                    longitude=destination.get("longitude"),
                    distance_km=destination.get("distance_km"),
                    address=city,
                    tags=destination.get("tags", []),
                    source=self.name,
                )
            )
        return places

    def reverse_geocode(self, latitude: float, longitude: float) -> ReverseGeocodeResponse:
        return ReverseGeocodeResponse(provider=self.name, formatted_address=None, source=self.name)

    def weather(self, city: str | None = None, adcode: str | None = None) -> WeatherResponse:
        return WeatherResponse(provider=self.name, city=city, adcode=adcode, source="fallback")

    def walking_route(self, origin_latitude: float, origin_longitude: float, destination_latitude: float, destination_longitude: float) -> RouteResponse:
        distance = haversine_km(origin_latitude, origin_longitude, destination_latitude, destination_longitude)
        return RouteResponse(
            provider=self.name,
            distance_meters=int(distance * 1000),
            duration_seconds=int(distance * 1000 / 1.2),
            steps=["本地 fallback：按直线距离估算，未调用真实路线规划。"],
            source="fallback",
        )


class AmapPlaceProvider:
    name = "amap"

    def nearby(self, latitude: float, longitude: float, keyword: str, radius_km: float) -> list[NearbyPlace]:
        if not settings.amap_api_key:
            return []

        params: dict[str, str | int] = {
            "key": settings.amap_api_key,
            "location": f"{longitude},{latitude}",
            "radius": int(radius_km * 1000),
            "offset": 20,
            "page": 1,
            "extensions": "base",
        }
        poi_type = _amap_type_for_keyword(keyword)
        if poi_type:
            params["types"] = poi_type
        else:
            params["keywords"] = keyword
        with httpx.Client(timeout=8) as client:
            response = client.get("https://restapi.amap.com/v3/place/around", params=params)
            response.raise_for_status()
            payload = response.json()
        self._ensure_success(payload)

        pois = payload.get("pois", [])
        return [self._to_place(poi, latitude, longitude) for poi in pois]

    def text_search(self, keyword: str, city: str | None, limit: int) -> list[NearbyPlace]:
        if not settings.amap_api_key:
            return []

        params: dict[str, str | int] = {
            "key": settings.amap_api_key,
            "offset": limit,
            "page": 1,
            "extensions": "base",
        }
        poi_type = _amap_type_for_keyword(keyword)
        if poi_type:
            params["types"] = poi_type
        else:
            params["keywords"] = keyword
        if city:
            params["city"] = city
        with httpx.Client(timeout=8) as client:
            response = client.get("https://restapi.amap.com/v3/place/text", params=params)
            response.raise_for_status()
            payload = response.json()
        self._ensure_success(payload)
        return [self._to_place(poi, None, None) for poi in payload.get("pois", [])]

    def reverse_geocode(self, latitude: float, longitude: float) -> ReverseGeocodeResponse:
        if not settings.amap_api_key:
            return ReverseGeocodeResponse(provider=self.name, source="not-configured")

        params = {
            "key": settings.amap_api_key,
            "location": f"{longitude},{latitude}",
            "extensions": "base",
        }
        with httpx.Client(timeout=8) as client:
            response = client.get("https://restapi.amap.com/v3/geocode/regeo", params=params)
            response.raise_for_status()
            payload = response.json()
        self._ensure_success(payload)
        regeocode = payload.get("regeocode", {})
        component = regeocode.get("addressComponent", {})
        return ReverseGeocodeResponse(
            provider=self.name,
            formatted_address=regeocode.get("formatted_address"),
            country=component.get("country"),
            province=component.get("province"),
            city=_string_or_join(component.get("city")),
            district=component.get("district"),
            adcode=component.get("adcode"),
            source="amap",
        )

    def weather(self, city: str | None = None, adcode: str | None = None) -> WeatherResponse:
        if not settings.amap_api_key:
            return WeatherResponse(provider=self.name, city=city, adcode=adcode, source="not-configured")

        city_code = adcode or city
        if not city_code:
            return WeatherResponse(provider=self.name, source="missing-city")

        params = {
            "key": settings.amap_api_key,
            "city": city_code,
            "extensions": "base",
        }
        with httpx.Client(timeout=8) as client:
            response = client.get("https://restapi.amap.com/v3/weather/weatherInfo", params=params)
            response.raise_for_status()
            payload = response.json()
        self._ensure_success(payload)
        lives = payload.get("lives", [])
        if not lives:
            return WeatherResponse(provider=self.name, city=city, adcode=adcode, source="amap")
        live = lives[0]
        return WeatherResponse(
            provider=self.name,
            city=live.get("city"),
            adcode=live.get("adcode"),
            weather=live.get("weather"),
            temperature=live.get("temperature"),
            wind_direction=live.get("winddirection"),
            wind_power=live.get("windpower"),
            humidity=live.get("humidity"),
            report_time=live.get("reporttime"),
            source="amap",
        )

    def walking_route(self, origin_latitude: float, origin_longitude: float, destination_latitude: float, destination_longitude: float) -> RouteResponse:
        if not settings.amap_api_key:
            return RouteResponse(provider=self.name, source="not-configured")

        params = {
            "key": settings.amap_api_key,
            "origin": f"{origin_longitude},{origin_latitude}",
            "destination": f"{destination_longitude},{destination_latitude}",
        }
        with httpx.Client(timeout=8) as client:
            response = client.get("https://restapi.amap.com/v3/direction/walking", params=params)
            response.raise_for_status()
            payload = response.json()
        self._ensure_success(payload)
        paths = payload.get("route", {}).get("paths", [])
        if not paths:
            return RouteResponse(provider=self.name, source="amap")
        path = paths[0]
        steps = [step.get("instruction", "") for step in path.get("steps", []) if step.get("instruction")]
        return RouteResponse(
            provider=self.name,
            distance_meters=_safe_int(path.get("distance")),
            duration_seconds=_safe_int(path.get("duration")),
            steps=steps,
            source="amap",
        )

    def _to_place(self, poi: dict[str, Any], latitude: float | None, longitude: float | None) -> NearbyPlace:
        lon = None
        lat = None
        if poi.get("location") and "," in poi["location"]:
            lon_text, lat_text = poi["location"].split(",", 1)
            lon = float(lon_text)
            lat = float(lat_text)
        distance = haversine_km(latitude, longitude, lat, lon) if latitude is not None and longitude is not None and lat is not None and lon is not None else None
        return NearbyPlace(
            id=str(poi.get("id", "")),
            name=str(poi.get("name", "")),
            type="restaurant",
            latitude=lat,
            longitude=lon,
            distance_km=round(distance, 2) if distance is not None else None,
            address=poi.get("address"),
            tags=[tag for tag in str(poi.get("type", "")).split(";") if tag],
            source=self.name,
        )

    def _ensure_success(self, payload: dict[str, Any]) -> None:
        if str(payload.get("status", "1")) != "1":
            message = payload.get("info") or payload.get("infocode") or "Amap request failed"
            raise RuntimeError(str(message))


def _safe_int(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _string_or_join(value: Any) -> str | None:
    if isinstance(value, list):
        return ",".join(str(item) for item in value if item)
    if value:
        return str(value)
    return None


def _amap_type_for_keyword(keyword: str) -> str | None:
    if any(term in keyword for term in ["餐厅", "餐饮", "美食", "饭店", "吃饭"]):
        return "050000"
    if any(term in keyword for term in ["景点", "旅游", "公园", "博物馆", "游玩"]):
        return "110000"
    return None


def get_place_provider() -> PlaceProvider:
    if settings.amap_api_key or settings.strict_real_data:
        return AmapPlaceProvider()
    return LocalPlaceProvider()


def provider_capabilities() -> dict[str, dict[str, bool | str]]:
    fallback = "disabled" if settings.strict_real_data else "local-json"
    return {
        "places": {
            "active": bool(settings.amap_api_key),
            "source": "amap" if settings.amap_api_key else "not-configured",
            "fallback": fallback,
            "env": "AMAP_API_KEY",
        },
        "weather": {
            "active": bool(settings.amap_api_key),
            "source": "amap-weather" if settings.amap_api_key else "not-configured",
            "fallback": "disabled" if settings.strict_real_data else "empty-response",
            "env": "AMAP_API_KEY",
        },
        "routes": {
            "active": bool(settings.amap_api_key),
            "source": "amap-walking-route" if settings.amap_api_key else "not-configured",
            "fallback": "disabled" if settings.strict_real_data else "straight-line-estimate",
            "env": "AMAP_API_KEY",
        },
        "aigc": {
            "active": bool(settings.llm_api_key),
            "source": "openai-compatible-llm" if settings.llm_api_key else "not-configured",
            "fallback": "disabled" if settings.strict_real_data else "template-generator",
            "env": "LLM_API_KEY / LLM_BASE_URL / LLM_MODEL",
        },
        "shopping": {
            "active": True,
            "source": "aigc-generated-needs",
            "fallback": "disabled" if settings.strict_real_data else "local-json",
            "env": "PRODUCT_PROVIDER / LLM_API_KEY",
        },
        "strict_real_data": {
            "active": settings.strict_real_data,
            "source": "configuration",
            "fallback": "disabled" if settings.strict_real_data else "enabled-for-dev",
            "env": "STRICT_REAL_DATA",
        },
    }
