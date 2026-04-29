from __future__ import annotations

from typing import Protocol

from .aigc import generate_product_ideas
from .config import settings
from .data_loader import load_dataset
from .models import ProductItem, ProductProviderName


class ProductProvider(Protocol):
    name: str

    def search(self, keyword: str, budget: float | None, tags: list[str], limit: int, scenario: str = "shopping") -> list[ProductItem]:
        ...


class LocalProductProvider:
    name = "local-json"

    def search(self, keyword: str, budget: float | None, tags: list[str], limit: int, scenario: str = "shopping") -> list[ProductItem]:
        dataset = load_dataset()
        keyword_terms = [term for term in [keyword, *tags] if term]
        products: list[tuple[float, ProductItem]] = []

        for product in dataset["products"]:
            product_tags = product.get("tags", [])
            text = " ".join([product["name"], product.get("category", ""), *product_tags])
            keyword_score = sum(1 for term in keyword_terms if term in text)
            budget_score = 1.0 if budget is None or product.get("price", 0) <= budget else 0.4
            score = keyword_score + budget_score
            if score <= 0:
                continue
            products.append(
                (
                    score,
                    ProductItem(
                        id=product["id"],
                        name=product["name"],
                        provider=self.name,
                        category=product.get("category"),
                        price=product.get("price"),
                        tags=product_tags,
                        reason="来自本地示例商品库，匹配当前关键词和标签。",
                        purchase_hint="真实部署时可替换为用户自有商品库或电商链接。",
                        source="sample-data",
                    ),
                )
            )

        return [item for _, item in sorted(products, key=lambda pair: pair[0], reverse=True)[:limit]]


class AigcProductProvider:
    name = "aigc-generated"

    def search(self, keyword: str, budget: float | None, tags: list[str], limit: int, scenario: str = "shopping") -> list[ProductItem]:
        ideas = generate_product_ideas(keyword=keyword, scenario=scenario, budget=budget, tags=tags, limit=limit)
        products: list[ProductItem] = []
        for index, idea in enumerate(ideas, start=1):
            idea_tags = idea.get("tags", [])
            products.append(
                ProductItem(
                    id=f"aigc-{index:03d}",
                    name=str(idea.get("name", f"生成商品 {index}")),
                    provider=self.name,
                    category=str(idea.get("category", "生成商品")),
                    price=float(idea["price"]) if isinstance(idea.get("price"), (int, float)) else None,
                    tags=[str(tag) for tag in idea_tags] if isinstance(idea_tags, list) else [],
                    reason=str(idea.get("reason", "由 AIGC 根据当前生活目标生成。")),
                    purchase_hint=str(idea.get("purchase_hint", "购买前请自行比价并确认品牌、规格和评价。")),
                    source="aigc",
                )
            )
        return products


def get_product_provider(provider: ProductProviderName = "auto") -> ProductProvider:
    if provider in ("auto", "aigc"):
        return AigcProductProvider()
    return LocalProductProvider()


def product_provider_status() -> dict[str, dict[str, bool | str]]:
    return {
        "aigc": {
            "configured": bool(settings.llm_api_key),
            "implemented": True,
            "source": "openai-compatible-llm" if settings.llm_api_key else "not-configured",
            "fallback": "disabled" if settings.strict_real_data else "template-generator",
        },
        "local": {
            "configured": not settings.strict_real_data,
            "implemented": True,
            "source": "data/products.json",
            "fallback": "development-only",
        },
    }
