from __future__ import annotations

from app.cache import _cache_key


def test_cache_key_does_not_depend_on_secret_key() -> None:
    first = _cache_key(
        "amap",
        "https://restapi.amap.com/v3/place/around",
        {"key": "secret-a", "location": "118.904,31.936", "radius": 3000},
    )
    second = _cache_key(
        "amap",
        "https://restapi.amap.com/v3/place/around",
        {"key": "secret-b", "location": "118.904,31.936", "radius": 3000},
    )
    assert first == second
