from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx

from .config import settings
from .storage import get_cache, set_cache


def cached_get_json(provider: str, url: str, params: dict[str, Any], timeout: float = 8) -> dict[str, Any]:
    cache_key = _cache_key(provider, url, params)
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    with httpx.Client(timeout=timeout) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()

    if isinstance(payload, dict) and settings.provider_cache_ttl_seconds > 0:
        set_cache(
            cache_key=cache_key,
            provider=provider,
            payload=payload,
            ttl_seconds=settings.provider_cache_ttl_seconds,
        )
    return payload


def _cache_key(provider: str, url: str, params: dict[str, Any]) -> str:
    scrubbed = {key: value for key, value in params.items() if key.lower() not in {"key", "apikey", "api_key", "authorization"}}
    raw = json.dumps({"provider": provider, "url": url, "params": scrubbed}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
