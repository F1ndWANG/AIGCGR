from dataclasses import dataclass
import os
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    amap_api_key: str | None = os.getenv("AMAP_API_KEY")
    google_places_api_key: str | None = os.getenv("GOOGLE_PLACES_API_KEY")
    llm_api_key: str | None = os.getenv("LLM_API_KEY")
    llm_base_url: str | None = os.getenv("LLM_BASE_URL")
    llm_model: str = os.getenv("LLM_MODEL", "deepseek-v4-flash")
    product_provider: str = os.getenv("PRODUCT_PROVIDER", "aigc")
    strict_real_data: bool = os.getenv("STRICT_REAL_DATA", "false").lower() in {"1", "true", "yes", "on"}
    provider_cache_ttl_seconds: int = int(os.getenv("PROVIDER_CACHE_TTL_SECONDS", "300"))


settings = Settings()
