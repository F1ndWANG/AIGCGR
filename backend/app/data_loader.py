import json
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"


@lru_cache(maxsize=1)
def load_dataset() -> dict[str, Any]:
    return {
        "users": _load_json("users.json"),
        "restaurants": _load_json("restaurants.json"),
        "dishes": _load_json("dishes.json"),
        "products": _load_json("products.json"),
        "destinations": _load_json("destinations.json"),
    }


def _load_json(filename: str) -> Any:
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)

